from __future__ import annotations

from app.models.streaming import (
    StreamingDepartmentSummaryItem,
    StreamingDepartmentSummaryResponse,
    StreamingEventItem,
    StreamingEventsResponse,
    StreamingSummaryResponse,
    StreamingSupplierSummaryItem,
    StreamingSupplierSummaryResponse,
)

from app.repositories.streaming_repository import (
    read_streaming_department_summary,
    read_streaming_events,
    read_streaming_summary,
)

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
    summary = read_streaming_summary()

    return StreamingSummaryResponse(**summary)

def get_streaming_department_summary(
    *,
    fiscal_year: int | None = None,
    department: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> StreamingDepartmentSummaryResponse:

    if fiscal_year is None and not department:
        summary = read_streaming_department_summary()
        raw_items = summary.get("data", [])

        items = [
            StreamingDepartmentSummaryItem(**item)
            for item in raw_items
        ]

        total_count = len(items)
        paginated_items = items[offset : offset + limit]

        return StreamingDepartmentSummaryResponse(
            total_count=total_count,
            count=len(paginated_items),
            limit=limit,
            offset=offset,
            data=paginated_items,
        )

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

def get_streaming_supplier_summary(
    *,
    fiscal_year: int | None = None,
    supplier_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> StreamingSupplierSummaryResponse:
    events = read_streaming_events()

    if fiscal_year is not None:
        events = [
            event
            for event in events
            if event["fiscal_year"] == fiscal_year
        ]

    if supplier_name:
        supplier_query = supplier_name.casefold()

        events = [
            event
            for event in events
            if supplier_query
            in str(event["supplier_name"]).casefold()
        ]

    grouped_events: dict[str, list[dict[str, object]]] = {}

    for event in events:
        current_supplier_name = str(event["supplier_name"])

        grouped_events.setdefault(
            current_supplier_name,
            [],
        ).append(event)

    items = []

    for current_supplier_name, supplier_events in grouped_events.items():
        fiscal_years = [
            int(event["fiscal_year"])
            for event in supplier_events
        ]

        items.append(
            StreamingSupplierSummaryItem(
                supplier_name=current_supplier_name,
                event_count=len(supplier_events),
                total_payment_amount=round(
                    sum(
                        float(event["payment_amount"])
                        for event in supplier_events
                    ),
                    2,
                ),
                unique_departments=len(
                    {
                        str(event["department"])
                        for event in supplier_events
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

    return StreamingSupplierSummaryResponse(
        total_count=total_count,
        count=len(paginated_items),
        limit=limit,
        offset=offset,
        data=paginated_items,
    )