from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.streaming import StreamingEventsResponse
from app.services.streaming_service import get_streaming_events


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