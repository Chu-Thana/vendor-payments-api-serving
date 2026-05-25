# ===============================
# Standard library
# ===============================
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from time import perf_counter
from typing import Optional
from urllib.parse import urlencode
import uuid

# ===============================
# Third-party
# ===============================


from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import Response
from database.redshift import get_redshift_connection

# ===============================
# Local modules
# ===============================
import db
import db_pg
from cache import cache_health, cache_try_get, cache_try_set, make_key
from config import CACHE_ENABLED
from logging_setup import setup_logging
from schemas import (
    CategorySalesItem,
    CategorySalesResponse,
    CategorySort,
    DailySalesResponse,
    HealthDBResponse,
    MonthlySalesCursorResponse,
    MonthlySalesItem,
    MonthlySalesResponse,
    MonthlySort,
    RegionSalesItem,
    RegionSalesResponse,
    RegionSort,
    RegionSalesWarehouseResponse,
    RegionSalesWarehouseItem,
    DashboardRegionPerformanceItem,
    DashboardSalesTrendItem,
)

# ===============================
# Logging Setup
# ===============================
# Initialize structured logging configuration (formatters, handlers, levels)
logger = setup_logging()

# ===============================
# Application Lifecycle
# ===============================
@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Application lifecycle handler.

    Startup:
    - Ensure api_run_log table exists (Postgres)
    - Emit startup logs

    Shutdown:
    - Emit shutdown logs
    """
    # Startup
    try:
        db_pg.init_api_run_log_pg()
        logger.info("api_run_log initialized")
    except Exception as e:
        # Logging infra must never prevent the API from starting
        logger.warning("api_run_log init failed: %s", repr(e))

    logger.info("API started")
    logger.debug("DEBUG is enabled")

    yield

    # Shutdown
    logger.info("API shutdown")


app = FastAPI(
    title="Superstore Analytics API",
    version="0.1.0",
    lifespan=lifespan,
)

# ===============================
# Middleware
# ===============================

@app.middleware("http")
async def api_run_log_middleware(request: Request, call_next):
    """
    Global API request logging middleware.

    Captures:
    - request_ms (total request time)
    - query_ms, rows_processed, log_message (from request.state)
    - request_id (trace)
    - SUCCESS / FAILED based on status_code (>=400 => FAILED)

    Guarantees:
    - Never breaks the API even if DB logging fails
    """

    t0 = perf_counter()

    # Trace ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # default state (กันลืม set จาก endpoint)
    request.state.query_ms = None
    request.state.rows_processed = 0
    request.state.log_message = ""
    request.state.cache_status = None
    request.state.cache_key = None

    method = request.method
    endpoint = request.url.path
    query_string = str(request.url.query)
    qs_part = f"?{query_string}" if query_string else ""

    def build_msg(code: int, duration_ms: float, err_text: str | None = None) -> str:
        qms = getattr(request.state, "query_ms", None)
        extra = getattr(request.state, "log_message", "")

        message = f"{method} {endpoint} {code} request_ms={duration_ms:.2f} qs={qs_part}"
        if qms is not None:
            message += f" | query_ms={float(qms):.2f}"
        if extra:
            message += f" | {extra}"
        if err_text:
            message += f" | err={err_text}"
        return message

    def safe_db_log(
            *,
            log_status: str,
            msg_text: str,
            request_ms: float,
            http_status_code: int,
            err_text: str | None = None,
    ) -> None:
        try:
            db_pg.log_api_run_pg(
                status=log_status,
                rows_processed=getattr(request.state, "rows_processed", 0),
                request_ms=request_ms,
                query_ms=getattr(request.state, "query_ms", None),
                status_code=http_status_code,
                request_id=request_id,
                endpoint=endpoint,
                method=method,
                query_string=query_string,
                message=msg_text,
                error=err_text,
                cache_status=getattr(request.state, "cache_status", None),
                cache_key=getattr(request.state, "cache_key", None),
            )
        except Exception as exc:
            logger.exception(
                "api_run_log_write_failed_unexpected",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": endpoint,
                    "err": str(exc),
                },
            )

    def attach_headers(resp: Response) -> None:
        resp.headers["X-Request-ID"] = request_id

        qms = getattr(request.state, "query_ms", None)
        if qms is not None:
            resp.headers["X-Query-MS"] = f"{float(qms):.2f}"

        cache_status = getattr(request.state, "cache_status", None)
        if cache_status is not None:
            resp.headers["X-Cache"] = str(cache_status)

        cache_key = getattr(request.state, "cache_key", None)
        if cache_key is not None:
            resp.headers["X-Cache-Key"] = str(cache_key)

    # ---- main ----
    try:
        response = await call_next(request)
        elapsed_ms = (perf_counter() - t0) * 1000.0

        attach_headers(response)

        status_code = response.status_code
        status = "SUCCESS" if status_code < 400 else "FAILED"

        log_message = build_msg(status_code, elapsed_ms)
        safe_db_log(
            log_status=status,
            msg_text=log_message,
            request_ms=elapsed_ms,
            http_status_code=status_code,
        )
        return response

    except HTTPException as e:
        # Preserve original HTTPException semantics
        elapsed_ms = (perf_counter() - t0) * 1000.0

        error_text = f"{type(e).__name__}: {e.detail}"
        log_message = build_msg(e.status_code, elapsed_ms, error_text)
        safe_db_log(
            log_status="FAILED",
            msg_text=log_message,
            request_ms=elapsed_ms,
            http_status_code=e.status_code,
            err_text=error_text,
        )
        raise

    except Exception as e:
        elapsed_ms = (perf_counter() - t0) * 1000.0

        error_text = f"{type(e).__name__}: {e}"
        log_message = build_msg(500, elapsed_ms, error_text)
        safe_db_log(
            log_status="FAILED",
            msg_text=log_message,
            request_ms=elapsed_ms,
            http_status_code=500,
            err_text=error_text,
        )
        raise

# ===============================
# Health / Operational Endpoints
# ===============================

@app.get("/")
def root():
    return {"message": "Project 2 API is running"}

@app.get("/health/pg")
def health_pg(request: Request):
    """
    PostgreSQL health check endpoint.
    Returns 503 if the database is unreachable.
    """

    # ---- database execution ----
    t0 = perf_counter()
    ok = db_pg.health_pg()
    query_ms = (perf_counter() - t0) * 1000.0

    request.state.query_ms = round(query_ms, 2)

    if not ok:
        request.state.rows_processed = 0
        request.state.log_message = "health_pg_unavailable"
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable")

    # ---- middleware metrics ----
    request.state.rows_processed = 1
    request.state.log_message = "health_pg_ok"

    return {"ok": True}


@app.get(
    "/health/db",
    response_model=HealthDBResponse,
    responses={503: {"description": "Database unavailable"}},
)
def health_db(request: Request) -> HealthDBResponse:
    """
    Database health check endpoint.

    - Verify database connectivity
    - Validate required tables exist
    """

    # ---- database execution ----
    t0 = perf_counter()
    try:
        tables = db.check_db()
        tables = [t[0] if isinstance(t, (tuple, list)) else t for t in tables]
    except Exception as e:
        request.state.query_ms = round((perf_counter() - t0) * 1000.0, 2)
        request.state.rows_processed = 0
        request.state.log_message = f"health_db_failed error={type(e).__name__} msg={str(e)}"
        raise HTTPException(status_code=503, detail="DB unavailable")

    query_ms = (perf_counter() - t0) * 1000.0
    request.state.query_ms = round(query_ms, 2)

    # ---- validation ----
    has_clean = "superstore_clean" in tables

    # ---- middleware metrics ----
    request.state.rows_processed = len(tables)
    request.state.log_message = f"health_db_ok tables={len(tables)} has_superstore_clean={has_clean}"

    return HealthDBResponse(
        status="ok",
        db_tables=tables,
        has_superstore_clean=has_clean,
    )


@app.get("/health/cache", summary="Cache health check")
def health_cache(request: Request):
    """
    Cache (Redis) health check endpoint.
    """

    # ---- cache execution ----
    t0 = perf_counter()
    ok = cache_health()
    query_ms = (perf_counter() - t0) * 1000.0
    request.state.query_ms = round(query_ms, 2)

    # ---- cache disabled ----
    if not CACHE_ENABLED:
        request.state.rows_processed = 0
        request.state.log_message = "health_cache_disabled"
        return {
            "cache_enabled": False,
            "redis_ok": None,
            "status": "disabled",
        }

    # ---- redis failed ----
    if not ok:
        request.state.rows_processed = 0
        request.state.log_message = "health_cache_fail"
        raise HTTPException(status_code=503, detail="Redis unavailable")

    # ---- success ----
    request.state.rows_processed = 1
    request.state.log_message = "health_cache_ok"
    return {
        "cache_enabled": True,
        "redis_ok": ok,
        "status": "ok" if ok else "fail",
    }

@app.get("/health/redshift")
def health_redshift():
    conn = None
    cursor = None

    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        return {"status": "ok", "service": "redshift"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


@app.get("/metrics", summary="Operational metrics (last N minutes)")
def get_metrics(window_minutes: int = Query(60, ge=1, le=1440)):
    return db_pg.get_metrics_summary_pg(window_minutes=window_minutes)

# ===============================
# Sales Analytics APIs
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

    # ---- database execution ----
    t0 = perf_counter()
    sales_date_str = sales_date.isoformat()
    result = db.get_daily_sales(sales_date_str, decimals)
    query_ms = (perf_counter() - t0) * 1000.0

    request.state.query_ms = round(query_ms, 2)

    if result is None:
        request.state.rows_processed = 0
        request.state.log_message = f"daily_sales_no_data sales_date={sales_date_str} decimals={decimals}"
        raise HTTPException(status_code=404, detail="No data for this date")

    # ---- middleware metrics ----
    request.state.rows_processed = 1
    request.state.log_message = f"daily_sales_ok sales_date={sales_date_str} decimals={decimals}"

    return DailySalesResponse(
        sales_date=result["sales_date"],
        total_orders=result["total_orders"],
        total_revenue=result["total_revenue"],
    )


@app.get(
    "/sales/monthly/offset",
    response_model=MonthlySalesResponse,
    summary="Get monthly sales summary (page-based)",
    description="Return monthly sales & profit with page-based pagination",
    responses={
        400: {"description": "Bad Request (invalid pagination or date range)"},
        404: {"description": "No data for this period"},
    },
)
def get_sales_monthly_offset(
    request: Request,
    start: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    end: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="YYYY-MM"),
    decimals: int = Query(2, ge=0, le=6, description="Decimal places (0-6), default 2"),
    sort: MonthlySort = Query(MonthlySort.month_asc, description="Sort order"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    page: int = Query(1, ge=1, description="1-based page number"),
) -> MonthlySalesResponse:

    t0 = perf_counter()

    # ---- validation ----
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    offset = (page - 1) * limit

    cache_key = make_key(
        prefix="p2:sales:monthly:offset",
        start=start,
        end=end,
        decimals=decimals,
        sort=sort.value,
        limit=limit,
        page=page,
    )
    request.state.cache_key = cache_key

    # ---- cache lookup ----
    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, dict):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms

        cached_resp = MonthlySalesResponse(**cached)
        cached_resp = cached_resp.model_copy(update={
            "cache_status": "HIT",
            "query_ms": hit_qms,
        })

        request.state.rows_processed = int(getattr(cached_resp, "count", 0))
        request.state.log_message = (
            f"category_cache_hit start={start} end={end} decimals={decimals} sort={sort.value} "
            f"limit={limit} page={page}"
        )
        return cached_resp

    # ---- database execution ----
    try:
        data, has_more, current_page, total_count, total_pages = db.get_sales_monthly(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_bad_request error={str(e)}"
        raise HTTPException(status_code=400, detail=str(e))

    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    # ---- pagination guard ----
    if total_count > 0 and page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_page_out_of_range start={start} end={end} "
            f"page={page} total_pages={total_pages}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"page must be <= total_pages ({total_pages})"
        )

    # ---- response construction ----
    prev_page = page - 1 if current_page > 1 else None
    next_page = page + 1 if current_page < total_pages else None

    query_ms = (perf_counter() - t0) * 1000.0
    generated_at = datetime.now(timezone.utc)
    items = [MonthlySalesItem(**row) for row in data]

    resp = MonthlySalesResponse(
        generated_at=generated_at,
        query_ms=round(query_ms, 2),
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
        cache_status=cache_status,
    )

    # ---- cache write ----
    cache_write = "skip"
    if CACHE_ENABLED and cache_status == "MISS":
        cache_write = cache_try_set(cache_key, jsonable_encoder(resp))

    # ---- middleware metrics ----
    request.state.query_ms = round(query_ms, 2)
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"monthly_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} page={page} offset={offset} count={len(data)} "
        f"has_more={has_more} total_count={total_count} total_pages={total_pages} "
        f"cache_status={cache_status} cache_write={cache_write}"
    )

    return resp


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
    t0 = perf_counter()

    # ---- validation ----
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"monthly_cursor_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    cache_key = make_key(
        prefix="p2:sales:monthly:cursor",
        start=start,
        end=end,
        decimals=decimals,
        sort=sort.value,
        limit=limit,
        cursor=cursor or "none",
    )
    request.state.cache_key = cache_key

    # ---- cache lookup ----
    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, dict):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms

        cached_resp = MonthlySalesCursorResponse(**cached)
        cached_resp = cached_resp.model_copy(update={
            "cache_status": "HIT",
            "query_ms": hit_qms,
        })
        request.state.log_message = (
            f"monthly_cursor_cache_hit start={start} end={end} "
            f"decimals={decimals} sort={sort.value} limit={limit}"
        )
        return cached_resp

    # ---- database execution ----
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

    if not data:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"monthly_cursor_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} cursor={'set' if cursor else 'none'}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    next_url = None
    if next_cursor:
        base_url = str(request.base_url).rstrip("/") + request.url.path
        q = urlencode(
            {
                "start": start,
                "end": end,
                "decimals": decimals,
                "sort": sort.value,
                "limit": limit,
                "cursor": next_cursor,
            }
        )
        next_url = f"{base_url}?{q}"

    query_ms = (perf_counter() - t0) * 1000.0
    generated_at = datetime.now(timezone.utc)

    items = [MonthlySalesItem(**row) for row in data]

    # ---- response construction ----
    resp = MonthlySalesCursorResponse(
        generated_at=generated_at,
        query_ms=round(query_ms, 2),
        start=start,
        end=end,
        decimals=decimals,
        limit=limit,
        sort=sort,
        cursor=cursor,
        has_more=has_more,
        next_cursor=next_cursor,
        next_url=next_url,
        count=len(data),
        data=items,
        cache_status=cache_status,
    )

    cache_write = "skip"
    # ---- cache write ----
    if CACHE_ENABLED and cache_status == "MISS":
        cache_write = cache_try_set(cache_key, jsonable_encoder(resp))

    # ---- middleware metrics ----
    request.state.query_ms = round(query_ms, 2)
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"monthly_cursor_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} count={len(data)} has_more={has_more} "
        f"cursor={'set' if cursor else 'none'} next_cursor={'set' if next_cursor else 'none'} "
        f"cache_status={cache_status} cache_write={cache_write}"
    )

    return resp


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

    t0 = perf_counter()

    # ---- validation ----
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"region_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    offset = (page - 1) * limit

    cache_key = make_key(
        prefix="p2:sales:region:offset",
        start=start,
        end=end,
        decimals=decimals,
        sort=sort.value,
        limit=limit,
        page=page,
    )
    request.state.cache_key = cache_key

    # ---- cache lookup ----
    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, dict):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms

        cached_resp = RegionSalesResponse(**cached)
        cached_resp = cached_resp.model_copy(update={
            "cache_status": "HIT",
            "query_ms": hit_qms,
        })

        request.state.rows_processed = int(getattr(cached_resp, "count", 0))
        request.state.log_message = (
            f"category_cache_hit start={start} end={end} decimals={decimals} sort={sort.value} "
            f"limit={limit} page={page}"
        )
        return cached_resp

    # ---- database execution ----
    try:
        data, has_more, total_count, total_pages = db.get_sales_by_region(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        request.state.rows_processed = 0
        request.state.log_message = f"region_bad_request error={str(e)}"
        raise HTTPException(status_code=400, detail=str(e))

    # ---- pagination guard (must run BEFORE "no data") ----
    if total_count == 0:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    if page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_page_out_of_range start={start} end={end} "
            f"page={page} total_pages={total_pages} "
            f"limit={limit} offset={offset}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"page must be <= total_pages ({total_pages})"
        )

    if not data:
        # safety net: should not happen if total_count>0, but keep it
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_no_rows start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page} offset={offset}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")


    # ---- response construction ----
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    query_ms = (perf_counter() - t0) * 1000.0
    generated_at = datetime.now(timezone.utc)
    items = [RegionSalesItem(**row) for row in data]

    resp = RegionSalesResponse(
        generated_at=generated_at,
        query_ms=round(query_ms, 2),
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
        cache_status=cache_status,
    )

    # ---- cache write ----
    cache_write = "skip"
    if CACHE_ENABLED and cache_status == "MISS":
        cache_write = cache_try_set(cache_key, jsonable_encoder(resp))

    # ---- middleware metrics ----
    request.state.query_ms = round(query_ms, 2)
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"region_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} page={page} offset={offset} count={len(data)} "
        f"has_more={has_more} total_count={total_count} total_pages={total_pages} "
        f"cache_status={cache_status} cache_write={cache_write}"
    )

    return resp


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

    t0 = perf_counter()

    # ---- validation ----
    if start > end:
        request.state.rows_processed = 0
        request.state.log_message = f"category_invalid_range start={start} end={end}"
        raise HTTPException(status_code=400, detail="Start date must <= end date (YYYY-MM)")

    offset = (page - 1) * limit

    cache_key = make_key(
        prefix="p2:sales:category:offset",
        start=start,
        end=end,
        decimals=decimals,
        sort=sort.value,
        limit=limit,
        page=page,
    )
    request.state.cache_key = cache_key

    # ---- cache lookup ----
    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, dict):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms

        cached_resp = CategorySalesResponse.model_validate(cached)
        cached_resp = cached_resp.model_copy(update={
            "cache_status": "HIT",
            "query_ms": hit_qms,
        })

        request.state.rows_processed = int(getattr(cached_resp, "count", 0))
        request.state.log_message = (
            f"category_cache_hit start={start} end={end} decimals={decimals} sort={sort.value} "
            f"limit={limit} page={page}"
        )
        return cached_resp

    # ---- database execution ----
    try:
        data, has_more, total_count, total_pages = db.get_sales_by_category(
            start=start,
            end=end,
            decimals=decimals,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        request.state.rows_processed = 0
        request.state.log_message = f"category_bad_request error={str(e)}"
        raise HTTPException(status_code=400, detail=str(e))

    # ---- pagination guard (must run BEFORE "no data") ----
    if total_count == 0:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_no_data start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    if page > total_pages:
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_page_out_of_range start={start} end={end} "
            f"page={page} total_pages={total_pages} "
            f"limit={limit} offset={offset}"
        )
        raise HTTPException(
            status_code=400,
            detail=f"page must be <= total_pages ({total_pages})"
        )

    if not data:
        # safety net: should not happen if total_count>0, but keep it
        request.state.rows_processed = 0
        request.state.log_message = (
            f"category_no_rows start={start} end={end} decimals={decimals} "
            f"sort={sort.value} limit={limit} page={page} offset={offset}"
        )
        raise HTTPException(status_code=404, detail="No data for this period")

    # ---- response construction ----
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None

    query_ms = (perf_counter() - t0) * 1000.0
    generated_at = datetime.now(timezone.utc)
    items = [CategorySalesItem(**row) for row in data]

    resp = CategorySalesResponse(
        generated_at=generated_at,
        query_ms=round(query_ms, 2),
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
        cache_status=cache_status,
    )

    # ---- cache write ----
    cache_write = "skip"
    if CACHE_ENABLED and cache_status == "MISS":
        cache_write = cache_try_set(cache_key, jsonable_encoder(resp))

    # ---- middleware metrics ----
    request.state.query_ms = round(query_ms, 2)
    request.state.rows_processed = len(data)
    request.state.log_message = (
        f"category_ok start={start} end={end} decimals={decimals} sort={sort.value} "
        f"limit={limit} page={page} offset={offset} count={len(data)} "
        f"has_more={has_more} total_count={total_count} total_pages={total_pages} "
        f"cache_status={cache_status} cache_write={cache_write}"
    )

    return resp

@app.get(
    path="/sales/by-region/warehouse",
    response_model=RegionSalesWarehouseResponse,
    summary="Get sales by region from Redshift mart",
    description="Query aggregated sales by region from Redshift warehouse layer"
)
def get_sales_by_region_warehouse(request: Request) -> RegionSalesWarehouseResponse:
    t0 = perf_counter()

    # ----- cache key -----
    cache_key = "p2:sales:region:warehouse"
    request.state.cache_key = cache_key

    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    # ----- cache HIT -----
    if cache_status == "HIT" and isinstance(cached, dict):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms

        cached_resp = RegionSalesWarehouseResponse.model_validate(cached)
        cached_resp = cached_resp.model_copy(update={
            "query_ms": hit_qms,
            "cache_status": "HIT"
        })

        request.state.rows_processed = int(getattr(cached_resp, "row_count", 0))
        request.state.log_message = "warehouse_region_cache_hit"

        return cached_resp

    # ----- database query -----
    conn = None
    cursor = None

    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT region, total_sales
            FROM mart_layer.sales_by_region
            ORDER BY total_sales DESC;
        """)

        rows = cursor.fetchall()

        data = [
            RegionSalesWarehouseItem(
                region=row[0],
                total_sales=float(row[1])
            )
            for row in rows
        ]

        query_ms = (perf_counter() - t0) * 1000
        generated_at = datetime.now(timezone.utc)

        resp = RegionSalesWarehouseResponse(
            source="redshift_mart",
            generated_at=generated_at,
            query_ms=round(query_ms, 2),
            row_count=len(data),
            data=data,
            cache_status=cache_status
        )

        # ----- cache write -----
        cache_write = "skip"
        if CACHE_ENABLED and cache_status == "MISS":
            cache_write = cache_try_set(cache_key, jsonable_encoder(resp))

        # ----- middleware metrics / logs -----
        request.state.query_ms = round(query_ms, 2)
        request.state.rows_processed = len(data)
        request.state.log_message = (
            f"warehouse_region_ok row_count={len(data)} "
            f"cache_status={cache_status} cache_write={cache_write}"
        )

        return resp

    except Exception as e:
        request.state.rows_processed = 0
        request.state.log_message = f"warehouse_region_error error={str(e)}"
        raise HTTPException(
            status_code=500,
            detail=f"Redshift query failed: {str(e)}"
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@app.get(
    path="/dashboard/region-performance",
    summary="Get dashboard-ready region performance from Redshift",
    response_model=list[DashboardRegionPerformanceItem]
)
def get_dashboard_region_performance(request: Request):
    t0 = perf_counter()

    cache_key = "p2:dashboard:region-performance"
    request.state.cache_key = cache_key

    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, list):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms
        request.state.rows_processed = len(cached)
        request.state.log_message = "dashboard_region_performance_cache_hit"

        return [DashboardRegionPerformanceItem.model_validate(row) for row in cached]

    conn = None
    cursor = None

    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT region, total_sales, total_profit
            FROM mart_layer.region_performance
            ORDER BY total_sales DESC;
        """)

        rows = cursor.fetchall()

        data = [
            DashboardRegionPerformanceItem(
                region=row[0],
                total_sales=float(row[1]),
                total_profit=float(row[2])
            )
            for row in rows
        ]

        query_ms = round((perf_counter() - t0) * 1000, 2)

        cache_write = "skip"
        if CACHE_ENABLED and cache_status == "MISS":
            cache_write = cache_try_set(cache_key, jsonable_encoder(data))

        request.state.query_ms = query_ms
        request.state.rows_processed = len(data)
        request.state.log_message = (
            f"dashboard_region_performance_ok rows={len(data)} "
            f"cache_status={cache_status} cache_write={cache_write}"
        )

        return data

    except Exception as e:
        request.state.rows_processed = 0
        request.state.log_message = f"dashboard_region_performance_error error={str(e)}"
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard region performance query failed: {str(e)}"
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
    
@app.get(
    path="/dashboard/sales-trend",
    summary="Get dashboard-ready monthly sales trend from Redshift",
    response_model=list[DashboardSalesTrendItem]
)
def get_dashboard_sales_trend(request: Request):
    t0 = perf_counter()

    cache_key = "p2:dashboard:sales-trend"
    request.state.cache_key = cache_key

    cached, cache_status = cache_try_get(cache_key)
    request.state.cache_status = cache_status

    if cache_status == "HIT" and isinstance(cached, list):
        hit_qms = round((perf_counter() - t0) * 1000, 2)
        request.state.query_ms = hit_qms
        request.state.rows_processed = len(cached)
        request.state.log_message = "dashboard_sales_trend_cache_hit"

        return [DashboardSalesTrendItem.model_validate(row) for row in cached]

    conn = None
    cursor = None

    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT year_month, total_sales, total_profit
            FROM mart_layer.sales_trend_monthly
            ORDER BY year_month;
        """)

        rows = cursor.fetchall()

        data = [
            DashboardSalesTrendItem(
                year_month=row[0],
                total_sales=float(row[1]),
                total_profit=float(row[2])
            )
            for row in rows
        ]

        query_ms = round((perf_counter() - t0) * 1000, 2)

        cache_write = "skip"
        if CACHE_ENABLED and cache_status == "MISS":
            cache_write = cache_try_set(cache_key, jsonable_encoder(data))

        request.state.query_ms = query_ms
        request.state.rows_processed = len(data)
        request.state.log_message = (
            f"dashboard_sales_trend_ok rows={len(data)} "
            f"cache_status={cache_status} cache_write={cache_write}"
        )

        return data

    except Exception as e:
        request.state.rows_processed = 0
        request.state.log_message = f"dashboard_sales_trend_error error={str(e)}"
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard sales trend query failed: {str(e)}"
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()