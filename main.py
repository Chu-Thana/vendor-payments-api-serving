from typing import Optional
from time import perf_counter
from datetime import datetime, timezone, date
from fastapi import FastAPI, HTTPException, Query, Request
import db
from urllib.parse import urlencode
from schemas import (DailySalesResponse, HealthDBResponse, MonthlySort,MonthlySalesItem, MonthlySalesResponse,
                     MonthlySalesCursorResponse, RegionSalesItem, RegionSalesResponse, RegionSort,
                     CategorySalesItem, CategorySalesResponse, CategorySort, ETLStatus)

app = FastAPI()

# ===============================
# Middleware
# ===============================
@app.middleware("http")
async def etl_run_log_middleware(request: Request, call_next):
    """
    Global request logging middleware (writes to etl_run_log).
    Endpoints may attach extra metadata via request.state:
      - rows_processed: int
      - query_ms: float
      - log_message: str
    """
    t0 = perf_counter()
    endpoint = request.url.path
    method = request.method
    query_string = str(request.url.query)

    try:
        response = await call_next(request)
        request_ms = round((perf_counter() - t0) * 1000, 2)

        rows_processed = getattr(request.state, "rows_processed", 0)
        query_ms = getattr(request.state, "query_ms", None)
        extra = getattr(request.state, "log_message", "")

        msg = (
            f"{method} {endpoint} {response.status_code} "
            f"request_ms={request_ms} qs={query_string}"
        )
        if query_ms is not None:
            msg += f" | query_ms={query_ms}"
        if extra:
            msg += f" | {extra}"

        db.log_etl_run(status=ETLStatus.SUCCESS, rows_processed=rows_processed, message=msg)
        return response

    except Exception as e:
        request_ms = round((perf_counter() - t0) * 1000, 2)

        rows_processed = getattr(request.state, "rows_processed", 0)
        query_ms = getattr(request.state, "query_ms", None)
        extra = getattr(request.state, "log_message", "")

        msg = (
            f"{method} {endpoint} ERROR "
            f"request_ms={request_ms} qs={query_string} "
            f"err={type(e).__name__}: {e}"
        )
        if query_ms is not None:
            msg += f" | query_ms={query_ms}"
        if extra:
            msg += f" | {extra}"

        db.log_etl_run(status=ETLStatus.FAILED, rows_processed=rows_processed, message=msg)
        raise



# ===============================
# Health Check
# ===============================

@app.get(
    "/health/db",
    response_model=HealthDBResponse,
    responses={503: {"description": "Database unavailable"}},
)
def health_db(request: Request) -> HealthDBResponse:
    """
    Health check endpoint for database connectivity and required tables.
    Used by monitoring systems and readiness probes to verify API availability.
    """

    try:
        tables = db.check_db()
        tables = [t[0] if isinstance(t, (tuple, list)) else t for t in tables]

    except Exception as e:
        # Attach metadata for middleware logging (failed case)
        request.state.rows_processed = 0
        request.state.log_message = f"health_check_failed error={type(e).__name__}"

        raise HTTPException(status_code=503, detail="DB unavailable")

    has_clean = "superstore_clean" in tables

    # Attach metadata for middleware logging (success case)
    request.state.rows_processed = len(tables)
    request.state.log_message = (
        f"health_check_ok tables={len(tables)} "
        f"has_superstore_clean={has_clean}"
    )

    return HealthDBResponse(
        status="ok",
        db_tables=tables,
        has_superstore_clean=has_clean,
    )


# ===============================
# Sales Endpoints
# ===============================

@app.get(
    "/sales/daily",
    response_model=DailySalesResponse,
    responses={
        404: {"description": "No data for this date"},
        422: {"description": "Validation error"},
    },
)
def get_sales_daily(
    request: Request,
    sales_date: date = Query(..., description="Target date in YYYY-MM-DD format"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
) -> DailySalesResponse:
    """
    Daily sales endpoint.
    Returns aggregated results for a specific date.
    Responds with 404 if no data is available.
    """

    sales_date_str = sales_date.isoformat()
    result = db.get_daily_sales(sales_date_str, decimals)

    if result is None:
        request.state.rows_processed = 0
        request.state.log_message = f"daily_sales_no_data sales_date={sales_date_str} decimals={decimals}"
        raise HTTPException(status_code=404, detail="No data for this date")

    # Daily returns a single aggregated record
    request.state.rows_processed = 1
    request.state.log_message = f"daily_sales_ok sales_date={sales_date_str} decimals={decimals}"

    return DailySalesResponse(
        sales_date=result["sales_date"],
        total_orders=result["total_orders"],
        total_revenue=result["total_revenue"],
    )

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
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: MonthlySort = Query(MonthlySort.month_asc, description="Sort order"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    page: int = Query(1, ge=1, description="1-based page number"),
) -> MonthlySalesResponse:
    """
    Offset-based monthly sales endpoint.
    Returns paginated aggregated results by month.
    """
    t0 = perf_counter()

    # Validate month range (lexicographic compare works for YYYY-MM format)
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    # Convert page-based pagination to SQL offset (DB layer uses limit/offset)
    offset = (page - 1) * limit

    # Query database for monthly aggregates (sort is validated via enum)
    data, has_more, current_page, total_count, total_pages = db.get_sales_monthly(
        start=start,
        end=end,
        decimals=decimals,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    # If page exceeds available pages but data exists in period
    if total_count > 0 and page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_page_out_of_range start={start} end={end} "
            f"page={page} total_pages={total_pages}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Page {page} exceeds total_pages {total_pages}"
        )

    # Return 404 when no data exists for the given period
    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page} offset={offset}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    # Derive navigation pages from computed pagination metadata
    prev_page = page - 1 if current_page > 1 else None
    next_page = page + 1 if current_page < total_pages else None

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc)

    # ✅ Attach metadata for middleware logging
    request.state.query_ms = query_ms
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"monthly_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} page={page} offset={offset} count={len(data)} "
        f"has_more={has_more} total_count={total_count} total_pages={total_pages}"
    )

    items = [MonthlySalesItem(**row) for row in data]

    return MonthlySalesResponse(
        generated_at=generated_at,
        query_ms=query_ms,
        start=start,
        end=end,
        decimals=decimals,
        sort=sort,
        limit=limit,
        offset=offset,
        current_page=current_page,
        prev_page=prev_page,
        next_page=next_page,
        count=len(data),
        has_more=has_more,
        total_count=total_count,
        total_pages=total_pages,
        data=items,
    )

@app.get(
    "/sales/monthly/cursor",
    response_model=MonthlySalesCursorResponse,
    summary="Get monthly sales summary (cursor-based)",
    description="Return monthly sales & profit using cursor-based pagination",
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
    sort: MonthlySort = Query(MonthlySort.month_asc, description="Sort order"),
    limit: int = Query(10, ge=1, le=100, description="Max items per page"),
    cursor: Optional[str] = Query(None, description="Opaque cursor from previous response"),
) -> MonthlySalesCursorResponse:
    """
    Cursor-based monthly sales endpoint.
    Returns efficiently paginated aggregated results by month.
    """
    t0 = perf_counter()

    # Validate month range (lexicographic compare works for YYYY-MM)
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_cursor_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    # Delegate cursor filtering + ordering logic to DB layer
    try:
        data, has_more, next_cursor = db.get_sales_monthly_cursor(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as e:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_cursor_bad_request error={str(e)}"
        raise HTTPException(status_code=400, detail=str(e))

    # Return 404 when no data exists for the given period
    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_cursor_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} cursor={'set' if cursor else 'none'}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc)

    # Build a developer-friendly next_url
    next_url = None
    if next_cursor:
        base_url = str(request.base_url).rstrip("/") + request.url.path
        q = urlencode({
            "start": start,
            "end": end,
            "decimals": decimals,
            "sort": sort.value,
            "limit": limit,
            "cursor": next_cursor,
        })
        next_url = f"{base_url}?{q}"

    # ✅ Attach metadata for middleware logging
    request.state.query_ms = query_ms
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"monthly_cursor_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} count={len(data)} has_more={has_more} "
        f"cursor={'set' if cursor else 'none'} next_cursor={'set' if next_cursor else 'none'}"
    )

    items = [MonthlySalesItem(**row) for row in data]

    return MonthlySalesCursorResponse(
        generated_at=generated_at,
        query_ms=query_ms,
        start=start,
        end=end,
        decimals=decimals,
        limit=limit,
        sort=sort,
        cursor=cursor,
        has_more=has_more,
        next_cursor=next_cursor,
        next_url=next_url,  # ต้องมีใน schema
        count=len(data),
        data=items,
    )

@app.get(
    "/sales/by-region",
    response_model=RegionSalesResponse,
    summary="Get sales summary grouped by region (page-based)",
    description=(
        "Return aggregated sales & profit grouped by region "
        "using offset-based pagination."
    ),
    responses={
        400: {"description": "Bad Request (invalid date range or parameters)"},
        404: {"description": "No data for this period"},
        422: {"description": "Validation error"},
    },
)
def get_sales_by_region(
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: RegionSort = Query(RegionSort.sales_desc, description="Sort order"),
    limit: int = Query(10, ge=1, le=100, description="Max items per page"),
    page: int = Query(1, ge=1, description="Page number"),
) -> RegionSalesResponse:
    """
    Offset-based regional sales endpoint.
    Returns paginated aggregated results grouped by region.
    """

    t0 = perf_counter()

    # Validate month range (lexicographic compare works for YYYY-MM format)
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"region_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    # Convert page-based pagination to SQL offset
    offset = (page - 1) * limit

    # Query DB layer
    data, has_more, total_count, total_pages = db.get_sales_by_region(
        start=start,
        end=end,
        decimals=decimals,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    # Validate page number against total_pages and return 400 if out of range.
    if total_pages and page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"region_page_exceeds page={page} total_pages={total_pages} "
            f"start={start} end={end} decimals={decimals} sort={sort.value} limit={limit}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Page {page} exceeds total_pages {total_pages}",
        )

    # Return 404 when no data exists for the given period
    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"region_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc)

    # ✅ Attach metadata for middleware logging
    request.state.query_ms = query_ms
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"region_ok start={start} end={end} decimals={decimals} "
        f"sort={sort.value} limit={limit} page={page} offset={offset} "
        f"count={len(data)} total_count={total_count} total_pages={total_pages}"
    )

    items = [RegionSalesItem(**row) for row in data]

    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    return RegionSalesResponse(
        generated_at=generated_at,
        query_ms=query_ms,
        start=start,
        end=end,
        decimals=decimals,
        limit=limit,
        sort=sort,
        offset=offset,
        page=page,
        prev_page=prev_page,
        next_page=next_page,
        count=len(data),
        has_more=has_more,
        total_count=total_count,
        total_pages=total_pages,
        data=items,
    )

@app.get(
    "/sales/by-category",
    response_model=CategorySalesResponse,
    summary="Get sales summary grouped by category",
    description="Return sales & profit grouped by category with offset/page pagination",
    responses={
        400: {"description": "Bad Request (invalid pagination or date range)"},
        404: {"description": "No data for this period"},
        422: {"description": "Validation error"},
    },
)
def get_sales_by_category(
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: CategorySort = Query(CategorySort.sales_desc, description="Sort order"),
    limit: int = Query(10, ge=1, le=100, description="Max items per page"),
    page: int = Query(1, ge=1, description="Page number"),
) -> CategorySalesResponse:
    """
    Offset-based categorical sales endpoint.
    Returns paginated aggregated results grouped by category.
    """
    t0 = perf_counter()

    # Validate month range
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"category_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    offset = (page - 1) * limit

    data, has_more, total_count, total_pages = db.get_sales_by_category(
        start=start,
        end=end,
        decimals=decimals,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    # Validate page number against total_pages and return 400 if out of range.
    if total_pages and page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_page_exceeds page={page} total_pages={total_pages} "
            f"start={start} end={end} decimals={decimals} sort={sort.value} limit={limit}"
        )
        raise HTTPException(status_code=400, detail=f"Page {page} exceeds total_pages {total_pages}")

    # Return 404 when no data exists for the given period
    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    query_ms = round((perf_counter() - t0) * 1000, 2)
    generated_at = datetime.now(timezone.utc)

    # ✅ Attach metadata for middleware logging
    request.state.query_ms = query_ms
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"category_ok start={start} end={end} decimals={decimals} "
        f"sort={sort.value} limit={limit} page={page} offset={offset} "
        f"count={len(data)} total_count={total_count} total_pages={total_pages}"
    )

    items = [CategorySalesItem(**row) for row in data]

    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    return CategorySalesResponse(
        generated_at=generated_at,
        query_ms=query_ms,
        start=start,
        end=end,
        decimals=decimals,
        limit=limit,
        sort=sort,
        offset=offset,
        page=page,
        prev_page=prev_page,
        next_page=next_page,
        count=len(data),
        has_more=has_more,
        total_count=total_count,
        total_pages=total_pages,
        data=items,
    )

