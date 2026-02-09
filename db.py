from database import get_conn
import json
import base64
from typing import Optional, Any

def _encode_cursor(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

def decode_cursor(cursor: str) -> dict:
    pad = "=" * ((4 - len(cursor) % 4) % 4)
    raw = base64.urlsafe_b64decode((cursor + pad).encode("utf-8"))
    return json.loads(raw.decode("utf-8"))

def get_sales_monthly_cursor(
        start: str,
        end: str,
        decimals: int,
        sort: str,
        limit: int,
        cursor: Optional[str]
):
    conn = get_conn()
    cur = conn.cursor()

    # map order by ให้ deterministic เสมอ (มี tie-breaker ด้วย month)
    order_by_map = {
        "month_asc": "month ASC",
        "month_desc": "month DESC",
        "sales_desc": "total_sales DESC, month DESC",
        "profit_desc": "total_profit DESC, month DESC",
    }
    if sort not in order_by_map:
        conn.close()
        raise ValueError("Invalid sort")

    order_by = order_by_map[sort]

    # base (ไม่มี WHERE ต่อจาก cursor)
    base_sql = """
    WITH agg AS (
        SELECT
            strftime('%Y-%m', order_date) AS month,
            SUM(sales)  AS total_sales,
            SUM(profit) AS total_profit
        FROM superstore_clean
        WHERE strftime('%Y-%m', order_date) BETWEEN ? AND ?
        GROUP BY month
    )
    SELECT month, total_sales, total_profit
    FROM agg
    """
    params: list[Any] = [start, end]

    where_sql = ""
    if cursor:
        c = decode_cursor(cursor)

        mismatches = {}
        if c.get("start") != start or c.get("end") != end or c.get("sort") != sort:
            conn.close()
            raise ValueError(
                json.dumps({
                    "error": "CURSOR_MISMATCH",
                    "message": "cursor does not match current query",
                    "mismatches": {
                        "start": {"cursor": c.get("start"), "request": start},
                        "end": {"cursor": c.get("end"), "request": end},
                        "sort": {"cursor": c.get("sort"), "request": sort},
                    },
                    "hint": "use next_cursor from the SAME start/end/sort request"
                })
            )

        if mismatches:
            conn.close()
            raise ValueError(json.dumps({
                "error": "CURSOR_MISMATCH",
                "message": "cursor does not match current query",
                "mismatches": mismatches,
                "hint": "use next_cursor from the same start/end/sort request",
            }))

        if cursor:
            c = decode_cursor(cursor)

            if sort == "month_asc":
                where_sql = "WHERE month > ?"
                params.append(c["m"])

            elif sort == "month_desc":
                where_sql = "WHERE month < ?"
                params.append(c["m"])

            elif sort == "sales_desc":
                where_sql = "WHERE (total_sales < ?) OR (total_sales = ? AND month < ?)"
                params.extend([c["s"], c["s"], c["m"]])

            elif sort == "profit_desc":
                where_sql = "WHERE (total_profit < ?) OR (total_profit = ? AND month < ?)"
                params.extend([c["p"], c["p"], c["m"]])

    sql = f"""
    {base_sql}
    {where_sql}
    ORDER BY {order_by}
    LIMIT ?;
    """
    params.append(limit + 1)
    rows = cur.execute(sql, params).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]

    # แปลงเป็น data (number จริง)
    data = [
        {
            "month": row["month"],
            "total_sales": round(float(row["total_sales"] or 0), decimals),
            "total_profit": round(float(row["total_profit"] or 0), decimals),
        }
        for row in rows
    ]

    # next_cursor = คีย์ของแถวสุดท้าย (ถ้ามีหน้าถัดไป)
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        ctx = {"start": start, "end": end, "sort": sort}

        if sort in ("month_asc", "month_desc"):
            next_cursor = _encode_cursor({**ctx, "m": last["month"]})

        elif sort == "sales_desc":
            next_cursor = _encode_cursor({**ctx, "s": float(last["total_sales"] or 0), "m": last["month"]})

        elif sort == "profit_desc":
            next_cursor = _encode_cursor({**ctx, "p": float(last["total_profit"] or 0), "m": last["month"]})

    conn.close()
    return data, has_more, next_cursor

def get_daily_sales(sales_date: str):
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute("""
        SELECT
            date(order_date) AS sales_date,
            COUNT(DISTINCT order_id) AS total_order,
            SUM(sales) AS total_revenue
        FROM superstore_clean
        WHERE date(order_date) = date(?)
        GROUP BY date(order_date)
    """, (sales_date,)).fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "sales_date": row["sales_date"],
        "total_order": row["total_order"],
        "total_revenue": float(row["total_revenue"] or 0)
    }

def get_sales_monthly(start: str, end: str, decimals: int, sort: str, limit: int, offset: int):
    conn = get_conn()
    cur = conn.cursor()

    order_by_map = {
        "month_asc": "month ASC",
        "month_desc": "month DESC",
        "sales_desc": "total_sales DESC",
        "profit_desc": "total_profit DESC",
    }
    order_by = order_by_map[sort]

    # 1) query data แบบมี pagination (ดึงมาเกิน 1 แถวเพื่อเช็ค has_more)
    data_sql = f"""
    SELECT
        strftime('%Y-%m', order_date) AS month,
        SUM(sales) AS total_sales,
        SUM(profit) AS total_profit
    FROM superstore_clean
    WHERE strftime('%Y-%m', order_date) BETWEEN ? AND ?
    GROUP BY month
    ORDER BY {order_by}
    LIMIT ? OFFSET ?;
    """
    rows = cur.execute(data_sql, (start, end, limit + 1, offset)).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]

    # 2) total_count (นับจำนวน “เดือน” หลัง group by)
    count_sql = """
    SELECT COUNT(*) AS total_count
    FROM (
        SELECT strftime('%Y-%m', order_date) AS month
        FROM superstore_clean
        WHERE strftime('%Y-%m', order_date) BETWEEN ? AND ?
        GROUP BY month
    ) t;
    """
    total_count = cur.execute(count_sql, (start, end)).fetchone()["total_count"]
    total_pages = (total_count + limit - 1) // limit  # ceil

    # 3) page + next_offset (ให้ FE ใช้ต่อได้เลย)
    page = (offset // limit) + 1

    # 4) ปั้น data (ส่งเป็น number)
    data = [
        {
            "month": row["month"],
            "total_sales": round((row["total_sales"] or 0), decimals),
            "total_profit": round((row["total_profit"] or 0), decimals),
        }
        for row in rows
    ]

    conn.close()
    return data, has_more, page, total_count, total_pages

def check_db():
    conn = get_conn()
    cur = conn.cursor()

    tables = cur.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name 
    """).fetchall()

    conn.close()
    return [t["name"] for t in tables]