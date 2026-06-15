from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.streaming import (
    StreamingDepartmentSummaryResponse,
    StreamingEventsResponse,
    StreamingSummaryResponse,
)

from app.services.streaming_service import (
    get_streaming_department_summary,
    get_streaming_events,
    get_streaming_summary,
)


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
    try:
        return get_streaming_events(
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


@router.get(
    "/summary",
    response_model=StreamingSummaryResponse,
    summary="Get streaming payment summary",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_summary_endpoint() -> StreamingSummaryResponse:
    try:
        return get_streaming_summary()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Streaming summary data is unavailable",
        ) from exc


@router.get(
    "/department-summary",
    response_model=StreamingDepartmentSummaryResponse,
    summary="Get streaming summary by department",
    responses={
        500: {"description": "Streaming data file unavailable"},
    },
)
def read_streaming_department_summary_endpoint(
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
    try:
        return get_streaming_department_summary(
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