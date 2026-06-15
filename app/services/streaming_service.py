from __future__ import annotations

from app.models.streaming import (
    StreamingDedupCount,
    StreamingDepartmentSummaryItem,
    StreamingDepartmentSummaryResponse,
    StreamingEventItem,
    StreamingEventsResponse,
    StreamingSummaryResponse,
    StreamingYearCount,
)

from app.repositories.streaming_repository import read_streaming_events

from collections import Counter

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

def get_streaming_summary() -> StreamingSummaryResponse:
    events = read_streaming_events()

    if not events:
        raise ValueError("Streaming sample contains no events")

    year_counts = Counter(
        int(event["fiscal_year"])
        for event in events
    )

    dedup_counts = Counter(
        str(event["dedup_status"])
        for event in events
    )

    fiscal_years = list(year_counts)

    total_payment_amount = round(
        sum(
            float(event["payment_amount"])
            for event in events
        ),
        2,
    )

    return StreamingSummaryResponse(
        total_events=len(events),
        total_payment_amount=total_payment_amount,
        unique_departments=len(
            {
                str(event["department"])
                for event in events
            }
        ),
        unique_suppliers=len(
            {
                str(event["supplier_name"])
                for event in events
            }
        ),
        minimum_fiscal_year=min(fiscal_years),
        maximum_fiscal_year=max(fiscal_years),
        events_by_fiscal_year=[
            StreamingYearCount(
                fiscal_year=fiscal_year,
                event_count=event_count,
            )
            for fiscal_year, event_count
            in sorted(year_counts.items())
        ],
        events_by_dedup_status=[
            StreamingDedupCount(
                dedup_status=dedup_status,
                event_count=event_count,
            )
            for dedup_status, event_count
            in sorted(dedup_counts.items())
        ],
    )

def get_streaming_department_summary(
    *,
    fiscal_year: int | None = None,
    department: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> StreamingDepartmentSummaryResponse:
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

    grouped_events: dict[str, list[dict[str, object]]] = {}

    for event in events:
        department_name = str(event["department"])

        grouped_events.setdefault(
            department_name,
            [],
        ).append(event)

    items = []

    for department_name, department_events in grouped_events.items():
        fiscal_years = [
            int(event["fiscal_year"])
            for event in department_events
        ]

        items.append(
            StreamingDepartmentSummaryItem(
                department=department_name,
                event_count=len(department_events),
                total_payment_amount=round(
                    sum(
                        float(event["payment_amount"])
                        for event in department_events
                    ),
                    2,
                ),
                unique_suppliers=len(
                    {
                        str(event["supplier_name"])
                        for event in department_events
                    }
                ),
                minimum_fiscal_year=min(fiscal_years),
                maximum_fiscal_year=max(fiscal_years),
            )
        )

    items.sort(
        key=lambda item: item.event_count,
        reverse=True,
    )

    total_count = len(items)
    paginated_items = items[offset : offset + limit]

    return StreamingDepartmentSummaryResponse(
        total_count=total_count,
        count=len(paginated_items),
        limit=limit,
        offset=offset,
        data=paginated_items,
    )