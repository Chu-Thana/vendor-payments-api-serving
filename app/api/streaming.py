from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from app.models.streaming import (
    StreamingDepartmentSummaryResponse,
    StreamingEventsResponse,
    StreamingSummaryResponse,
    StreamingSupplierSummaryResponse,
)

from app.services.streaming_service import (
    get_streaming_department_summary,
    get_streaming_events,
    get_streaming_summary,
    get_streaming_supplier_summary,
)

from app.cache.in_memory import api_response_cache
from app.cache.keys import build_cache_key
from app.config import API_CACHE_TTL_SECONDS

router = APIRouter(
    prefix="/api/v1/streaming",
    tags=["Streaming Analytics"],
)


@router.get(
    "/events",
    response_model=StreamingEventsResponse,
    summary="Get streaming payment events",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_events_endpoint(
    response: Response,
    fiscal_year: int | None = Query(
        default=None,
        description="Filter by fiscal year",
    ),
    department: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by department name",
    ),
    supplier_name: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by supplier name",
    ),
    dedup_status: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by deduplication status",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of events to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip",
    ),
) -> StreamingEventsResponse:
    cache_key = build_cache_key(
        "streaming:events",
        fiscal_year=fiscal_year,
        department=department,
        supplier_name=supplier_name,
        dedup_status=dedup_status,
        limit=limit,
        offset=offset,
    )

    cached_result = api_response_cache.get(cache_key)

    if cached_result is not None:
        response.headers["X-Cache-Status"] = "HIT"
        return cached_result

    try:
        result = get_streaming_events(
            fiscal_year=fiscal_year,
            department=department,
            supplier_name=supplier_name,
            dedup_status=dedup_status,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Streaming sample data is unavailable",
        ) from exc

    api_response_cache.set(
        key=cache_key,
        value=result,
        ttl_seconds=API_CACHE_TTL_SECONDS,
    )

    response.headers["X-Cache-Status"] = "MISS"

    return result


@router.get(
    "/summary",
    response_model=StreamingSummaryResponse,
    summary="Get streaming payment summary",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_summary_endpoint(
    response: Response,
) -> StreamingSummaryResponse:
    cache_key = build_cache_key(
        "streaming:summary",
    )

    cached_result = api_response_cache.get(cache_key)

    if cached_result is not None:
        response.headers["X-Cache-Status"] = "HIT"
        return cached_result

    try:
        result = get_streaming_summary()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Streaming summary data is unavailable",
        ) from exc

    api_response_cache.set(
        key=cache_key,
        value=result,
        ttl_seconds=API_CACHE_TTL_SECONDS,
    )

    response.headers["X-Cache-Status"] = "MISS"

    return result


@router.get(
    "/department-summary",
    response_model=StreamingDepartmentSummaryResponse,
    summary="Get streaming summary by department",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_department_summary_endpoint(
    response: Response,
    fiscal_year: int | None = Query(
        default=None,
        description="Filter by fiscal year",
    ),
    department: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by department name",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of departments to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of departments to skip",
    ),
) -> StreamingDepartmentSummaryResponse:
    cache_key = build_cache_key(
        "streaming:department-summary",
        fiscal_year=fiscal_year,
        department=department,
        limit=limit,
        offset=offset,
    )

    cached_result = api_response_cache.get(cache_key)

    if cached_result is not None:
        response.headers["X-Cache-Status"] = "HIT"
        return cached_result

    try:
        result = get_streaming_department_summary(
            fiscal_year=fiscal_year,
            department=department,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Streaming department summary data is unavailable",
        ) from exc

    api_response_cache.set(
        key=cache_key,
        value=result,
        ttl_seconds=API_CACHE_TTL_SECONDS,
    )

    response.headers["X-Cache-Status"] = "MISS"

    return result


@router.get(
    "/supplier-summary",
    response_model=StreamingSupplierSummaryResponse,
    summary="Get streaming summary by supplier",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_supplier_summary_endpoint(
    response: Response,
    fiscal_year: int | None = Query(
        default=None,
        description="Filter by fiscal year",
    ),
    supplier_name: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by supplier name",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of suppliers to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of suppliers to skip",
    ),
) -> StreamingSupplierSummaryResponse:
    cache_key = build_cache_key(
        "streaming:supplier-summary",
        fiscal_year=fiscal_year,
        supplier_name=supplier_name,
        limit=limit,
        offset=offset,
    )

    cached_result = api_response_cache.get(cache_key)

    if cached_result is not None:
        response.headers["X-Cache-Status"] = "HIT"
        return cached_result

    try:
        result = get_streaming_supplier_summary(
            fiscal_year=fiscal_year,
            supplier_name=supplier_name,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Streaming supplier summary data is unavailable",
        ) from exc

    api_response_cache.set(
        key=cache_key,
        value=result,
        ttl_seconds=API_CACHE_TTL_SECONDS,
    )

    response.headers["X-Cache-Status"] = "MISS"

    return result