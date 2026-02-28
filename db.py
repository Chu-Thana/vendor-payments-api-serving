import json
import base64
from database import get_conn
from typing import Optional, Any
from fastapi import HTTPException
from schemas import MonthlySort, RegionSort, CategorySort

# ===============================
# Cursor Utilities (Internal)
# ===============================

def _encode_cursor(payload: dict[str, Any]) -> str:
    """
    Encodes a cursor payload into a URL-safe Base64 string.
    Used for stateless cursor-based pagination.
    """
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_cursor(cursor: str) -> dict[str, Any]:
    """
    Decode base64 cursor string back into payload dictionary.

    Raises:
        HTTPException(400) if cursor is malformed or invalid.
    """
    try:
        # Restore base64 padding if removed
        pad = "=" * ((4 - len(cursor) % 4) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode("utf-8"))
        payload = json.loads(raw.decode("utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Cursor payload must be a JSON object")

        return payload

    except Exception:
        # Avoid leaking internal errors; treat all decode failures as bad request
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_CURSOR",
                "message": "Malformed or invalid cursor value",
            },
        )


# ===============================
# Health checks
# ===============================

def check_db() -> list[str]:
    """
    Retrieves all table names from the SQLite database.
    Used by the /health/db endpoint.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

    return [r["name"] for r in rows]


# ===============================
# Core Sales Queries
# ===============================

def get_daily_sales(
        sales_date: str,
        decimals: int
) -> dict | None:
    """
    Retrieves aggregated daily sales data for a given date.
    Returns None if no data is found.
    """
    sql = """
    SELECT
        ? AS sales_date,
        COUNT(DISTINCT order_id) AS total_orders,
        ROUND(SUM(sales), ?) AS total_revenue
    FROM superstore_clean
    WHERE strftime('%Y-%m-%d', order_date) = ?
    """

    with get_conn() as conn:
        cur = conn.cursor()
        row = cur.execute(sql, (sales_date, decimals, sales_date)).fetchone()

    # If no rows match, SUM(sales) will be NULL; treat as no data
    if row is None or row["total_revenue"] is None:
        return None

    return {
        "sales_date": row["sales_date"],
        "total_orders": row["total_orders"],
        "total_revenue": float(row["total_revenue"]),
    }


def get_sales_monthly(
    start: str,
    end: str,
    decimals: int,
    sort: MonthlySort,
    limit: int,
    offset: int,
) -> tuple[list[dict], bool, int, int, int]:

    """
    Retrieves offset-based paginated monthly sales summary
    within the specified date range.

    Returns aggregated results along with pagination metadata.
    """

    with get_conn() as conn:
        cur = conn.cursor()

        # Whitelist sort options to safe ORDER BY clauses (prevents SQL injection)
        order_by_map = {
            MonthlySort.month_asc: "month ASC",
            MonthlySort.month_desc: "month DESC",
            MonthlySort.sales_desc: "total_sales DESC",
            MonthlySort.profit_desc: "total_profit DESC",
        }
        # sort validated by enum in API layer
        try:
            order_by = order_by_map[sort]
        except KeyError:
            raise ValueError("Invalid sort option")

        # Fetch limit+1 rows to determine has_more (offset pagination)
        base_sql = f"""
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

        rows = cur.execute(base_sql, (start, end, limit + 1, offset)).fetchall()

        has_more = len(rows) > limit
        rows = rows[:limit]

        # Total number of grouped months (for pagination metadata)
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

        total_pages = max(1, (total_count + limit - 1) // limit)
        page = (offset // limit) + 1

        data = [
            {
                "month": row["month"],
                "total_sales": round((row["total_sales"] or 0), decimals),
                "total_profit": round((row["total_profit"] or 0), decimals),
            }
            for row in rows
        ]
        return data, has_more, page, total_count, total_pages


# ===============================
# Dimension-based Analytics
# ===============================

def get_sales_monthly_cursor(
    start: str,
    end: str,
    decimals: int,
    sort: MonthlySort,
    limit: int,
    cursor: Optional[str],
) -> tuple[list[dict], bool, Optional[str]]:
    """
    Cursor-based monthly aggregation endpoint.
    Uses last-seen row keys instead of OFFSET for efficient pagination.
    """

    # Whitelist sort options to safe ORDER BY clauses (prevents SQL injection)
    order_by_map = {
        MonthlySort.month_asc: "month ASC",
        MonthlySort.month_desc: "month DESC",
        MonthlySort.sales_desc: "total_sales DESC, month DESC",
        MonthlySort.profit_desc: "total_profit DESC, month DESC",
    }

    if sort not in order_by_map:
        raise HTTPException(status_code=400, detail="Invalid sort")

    order_by = order_by_map[sort]

    # Base query: aggregate by month first, then apply cursor filtering + ordering
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
        # Decode cursor and enforce query-parameter match
        c = _decode_cursor(cursor)

        # Enforce deterministic pagination: required keys depend on sort
        if (
                c.get("start") != start
                or c.get("end") != end
                or c.get("sort") != sort.value
                or c.get("limit") != limit
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "CURSOR_MISMATCH",
                    "message": "cursor does not match current query parameters",
                },
            )

        # For deterministic pagination, different sorts require different cursor keys
        required_by_sort = {
            MonthlySort.month_asc: ("m",),
            MonthlySort.month_desc: ("m",),
            MonthlySort.sales_desc: ("s", "m"),
            MonthlySort.profit_desc: ("p", "m"),
        }

        required = required_by_sort[sort]
        missing = [k for k in required if c.get(k) is None]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_CURSOR",
                    "message": "cursor payload missing required fields",
                    "missing_fields": missing,
                },
            )

        m = c.get("m")

        # Apply cursor filter based on chosen sort
        if sort == MonthlySort.month_asc:
            where_sql = "WHERE month > ?"
            params.append(m)

        elif sort == MonthlySort.month_desc:
            where_sql = "WHERE month < ?"
            params.append(m)

        elif sort == MonthlySort.sales_desc:
            s = c.get("s")
            where_sql = "WHERE (total_sales < ?) OR (total_sales = ? AND month < ?)"
            params.extend([s, s, m])

        elif sort == MonthlySort.profit_desc:
            p = c.get("p")
            where_sql = "WHERE (total_profit < ?) OR (total_profit = ? AND month < ?)"
            params.extend([p, p, m])

    with get_conn() as conn:
        cur = conn.cursor()
        # Fetch one extra row (limit + 1) to determine if more data exists
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

    # Build response items (apply rounding precision requested by the API)
    data = [
        {
            "month": row["month"],
            "total_sales": round(float(row["total_sales"] or 0), decimals),
            "total_profit": round(float(row["total_profit"] or 0), decimals),
        }
        for row in rows
    ]

    # Build next cursor from the last returned row (exclusive pagination)
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        ctx = {"start": start, "end": end, "sort": sort.value, "limit": limit}

        if sort in (MonthlySort.month_asc, MonthlySort.month_desc):
            next_cursor = _encode_cursor({**ctx, "m": last["month"]})

        elif sort == MonthlySort.sales_desc:
            next_cursor = _encode_cursor(
                {**ctx, "s": float(last["total_sales"] or 0), "m": last["month"]}
            )

        elif sort == MonthlySort.profit_desc:
            next_cursor = _encode_cursor(
                {**ctx, "p": float(last["total_profit"] or 0), "m": last["month"]}
            )

    return data, has_more, next_cursor


def get_sales_by_region(
    start: str,
    end: str,
    decimals: int,
    sort: RegionSort,
    limit: int,
    offset: int,
) -> tuple[list[dict], bool, int, int]:
    """
    Retrieves offset-based paginated sales aggregates grouped by region.
    """

    # Whitelist sort options to safe ORDER BY clauses
    order_by_map = {
        RegionSort.region_asc: "region ASC",
        RegionSort.sales_desc: "total_sales DESC",
        RegionSort.profit_desc: "total_profit DESC",
    }

    try:
        order_by = order_by_map[sort]
    except KeyError:
        raise ValueError("Invalid sort option")

    # Base aggregation query grouped by region
    base_sql = """
    SELECT
        region,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(sales) AS total_sales,
        SUM(profit) AS total_profit
    FROM superstore_clean
    WHERE strftime('%Y-%m', order_date) BETWEEN ? AND ?
    GROUP BY region
    """

    with get_conn() as conn:
        cur = conn.cursor()

        # Apply ordering and offset-based pagination (fetch limit+1 to detect has_more)
        sql = f"""
            {base_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """

        rows = cur.execute(sql, (start, end, limit + 1, offset)).fetchall()

        # Total grouped regions (for pagination metadata)
        total_count = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM ({base_sql}) t
            """,
            (start, end),
        ).fetchone()["count"]

    has_more = len(rows) > limit
    rows = rows[:limit]

    total_pages = max(1, (total_count + limit - 1) // limit)

    # Build response items with requested rounding precision
    data = [
        {
            "region": row["region"],
            "total_sales": round(float(row["total_sales"] or 0), decimals),
            "total_profit": round(float(row["total_profit"] or 0), decimals),
            "total_orders": row["total_orders"],
        }
        for row in rows
    ]

    return data, has_more, total_count, total_pages


def get_sales_by_category(
    start: str,
    end: str,
    decimals: int,
    sort: CategorySort,
    limit: int,
    offset: int,
) -> tuple[list[dict], bool, int, int]:
    """
    Retrieves offset-based paginated sales aggregates by category.
    Sorting is restricted to predefined enum values.
    """

    # Whitelist sort options to safe ORDER BY clauses
    order_by_map = {
        CategorySort.category_asc: "category ASC",
        CategorySort.sales_desc: "total_sales DESC",
        CategorySort.profit_desc: "total_profit DESC",
    }

    try:
        order_by = order_by_map[sort]
    except KeyError:
        raise ValueError("Invalid sort option")

    # Base aggregation query grouped by category
    base_sql = """
    SELECT
        category,
        COUNT(DISTINCT order_id) AS total_orders,
        SUM(sales) AS total_sales,
        SUM(profit) AS total_profit
    FROM superstore_clean
    WHERE strftime('%Y-%m', order_date) BETWEEN ? AND ?
    GROUP BY category
    """

    with get_conn() as conn:
        cur = conn.cursor()

        # Apply ordering and offset-based pagination (fetch limit+1 to detect has_more)
        sql = f"""
            {base_sql}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """

        rows = cur.execute(sql, (start, end, limit + 1, offset)).fetchall()

        # Total grouped categories (for pagination metadata)
        total_count = cur.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM ({base_sql}) t
            """,
            (start, end),
        ).fetchone()["count"]

    has_more = len(rows) > limit
    rows = rows[:limit]

    total_pages = max(1, (total_count + limit - 1) // limit)

    # Build response items with requested rounding precision
    data = [
        {
            "category": row["category"],
            "total_sales": round(float(row["total_sales"] or 0), decimals),
            "total_profit": round(float(row["total_profit"] or 0), decimals),
            "total_orders": row["total_orders"],
        }
        for row in rows
    ]

    return data, has_more, total_count, total_pages
