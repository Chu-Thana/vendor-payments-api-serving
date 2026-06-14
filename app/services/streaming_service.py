from __future__ import annotations

from app.models.streaming import (
    StreamingEventItem,
    StreamingEventsResponse,
)
from app.repositories.streaming_repository import read_streaming_events


def get_streaming_events(
    *,
    fiscal_year: int | None = None,
    department: str | None = None,
    supplier_name: str | None = None,
    dedup_status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> StreamingEventsResponse:
    events = read_streaming_events()

    if fiscal_year is not None:
        events = [
            event
            for event in events
            if event["fiscal_year"] == fiscal_year
        ]

    if department:
        department_query = department.casefold()

        events = [
            event
            for event in events
            if department_query
            in str(event["department"]).casefold()
        ]

    if supplier_name:
        supplier_query = supplier_name.casefold()

        events = [
            event
            for event in events
            if supplier_query
            in str(event["supplier_name"]).casefold()
        ]

    if dedup_status:
        dedup_query = dedup_status.casefold()

        events = [
            event
            for event in events
            if str(event["dedup_status"]).casefold()
            == dedup_query
        ]

    total_count = len(events)
    paginated_events = events[offset : offset + limit]

    items = [
        StreamingEventItem(**event)
        for event in paginated_events
    ]

    return StreamingEventsResponse(
        total_count=total_count,
        count=len(items),
        limit=limit,
        offset=offset,
        data=items,
    )