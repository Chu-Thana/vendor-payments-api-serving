import json
from typing import Optional
from time import perf_counter
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Request
import db
from schemas import DailySalesResponse, HealthDBResponse, MonthlySort, MonthlySalesResponse, MonthlySalesCursorResponse

app = FastAPI()

@app.get("/sales/daily",
         response_model=DailySalesResponse,
         summary="Get daily sales summary",
         description="Return total orders and revenue for a specific date"
         )
def get_sales_daily(
    date : str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
):
    result = db.get_daily_sales(date)

    if result is None:
        raise HTTPException(status_code=404, detail="No data for this date")

    return result

@app.get(
    "/sales/monthly",
    response_model=MonthlySalesResponse,
    summary="Get monthly sales summary (page-based)",
    description="Return monthly sales & profit with page-based pagination",
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

    # 1) Validate date range (YYYY-MM)
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    # 2) Convert page number to SQL offset (API controls paging)
    offset = (page - 1) * limit

    # 3) Query database for monthly aggregates
    data, has_more, page, total_count, total_pages = db.get_sales_monthly(
        start, end, decimals, sort.value, limit, offset
    )
    # Derive has_more from pagination metadata (API-level logic)
    has_more = page < total_pages
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    # Return 404 when no data exists for the given period
    if not data:
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Return offset-based paginated response
    return {
        "generated_at": generated_at,
        "query_ms": query_ms,
        "start": start,
        "end": end,
        "decimals": decimals,
        "sort": sort.value,
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

@app.get(
    "/sales/monthly/cursor",
    response_model=MonthlySalesCursorResponse,
    responses={
        400: {"description": "Bad Request (invalid cursor/date/sort)"},
        404: {"description": "No data for this period"},
    },
)
def get_sales_monthly_cursor(
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: MonthlySort = Query(MonthlySort.month_asc),
    limit: int = Query(10, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="opaque cursor from previous response"),
):
    # Start timing query execution (for API performance metrics)
    t0 = perf_counter()

    # Validate date range (string comparison works for YYYY-MM format)
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    try:
        # Query database using cursor-based pagination
        # DB is responsible for decoding / validating cursor
        data, _has_more, next_cursor, total_count = db.get_sales_monthly_cursor(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort.value,
            limit=limit,
            cursor=cursor,
        )
        # Cursor-based pagination rule:
        # if next_cursor exists, there is a next page
        has_more = next_cursor is not None

        # Total pages are calculated for informational purposes (portfolio-friendly)
        total_pages = (total_count + limit - 1) // limit

    except ValueError as e:
        # Convert DB-level validation errors into HTTP 400
        msg = str(e)
        try:
            detail = json.loads(msg)
        except json.JSONDecodeError:
            detail = {"error": "BAD_REQUEST", "message": msg}
        raise HTTPException(status_code=400, detail=detail)

    # No data found for given period (valid request, but empty result)
    if not data:
        raise HTTPException(status_code=404, detail="No data for this period")

    # Calculate query execution time (milliseconds)
    query_ms = round((perf_counter() - t0) * 1000, 2)

    # Standardized UTC timestamp for response metadata
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Prepare next page URL and curl command (developer-friendly)
    next_url = None
    next_curl = None
    base_url = str(request.url).split("?")[0]

    if next_cursor:
        next_url = (
            f"{base_url}"
            f"?start={start}&end={end}&decimals={decimals}"
            f"&sort={sort.value}&limit={limit}"
            f"&cursor={next_cursor}"
        )
        next_curl = f'curl -X GET "{next_url}" -H "accept: application/json"'

    # Return cursor-based paginated response
    return {
        "generated_at": generated_at,
        "query_ms": query_ms,
        "start": start,
        "end": end,
        "decimals": decimals,
        "limit": limit,
        "sort": sort.value,
        "cursor": cursor,
        "has_more": has_more,
        "next_cursor": next_cursor,
        "next_url": next_url,
        "next_curl": next_curl,
        "count": len(data),
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