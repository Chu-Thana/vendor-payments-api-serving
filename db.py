from database import get_conn

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
        "total_revenue": row["total_revenue"],
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