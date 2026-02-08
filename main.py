import db
from fastapi import FastAPI, HTTPException, Query
from schemas import DailySalesResponse, MonthlySalesResponse, HealthDBResponse, MonthlySort
from time import perf_counter
from datetime import datetime, timezone


app = FastAPI()

@app.get("/sales/daily",
         response_model=DailySalesResponse)
def get_sales_daily(
    date : str = Query(..., description="YYYY-MM-DD")
):
    result = db.get_daily_sales(date)

    if result is None:
        raise HTTPException(status_code=404, detail="No data for this date")

    return result

@app.get(
    "/sales/monthly",
    response_model=MonthlySalesResponse,
    responses={
        400: {"description": "Bad Request (invalid pagination or date range)"},
        404: {"description": "No data for this period"},
    },
)
def get_sales_monthly(
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: MonthlySort = Query(MonthlySort.month_asc),
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1, description="1-based page number"),
):
    t0 = perf_counter()

    # 1) validate date range ก่อน
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    # 2) page -> offset (API คุมเอง)
    offset = (page - 1) * limit

    # 3) query db
    data, has_more, page, total_count, total_pages = db.get_sales_monthly(
        start, end, decimals, sort.value, limit, offset
    )

    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    if not data:
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "generated_at": generated_at,
        "query_ms": query_ms,
        "start": start,
        "end": end,
        "decimals": decimals,
        "limit": limit,
        "offset": offset,
        "page": page,
        "prev_page": prev_page,
        "next_page": next_page,
        "count": len(data),
        "has_more": has_more,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": data,
    }

@app.get("/health/db",
         response_model=HealthDBResponse)
def health_db():
    tables = db.check_db()
    return {
        "status": "ok",
        "db_tables": tables,
        "has_superstore_clean": "superstore_clean" in tables,
    }