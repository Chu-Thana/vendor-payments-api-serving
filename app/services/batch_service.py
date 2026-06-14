from app.models.batch import (
    SpendingByDepartmentItem,
    SpendingByDepartmentResponse,
    SpendingByFiscalYearItem,
    SpendingByFiscalYearResponse,
)

from app.repositories.batch_repository import (
    read_spending_by_department,
    read_spending_by_fiscal_year,
)

def get_spending_by_fiscal_year() -> SpendingByFiscalYearResponse:
    records = read_spending_by_fiscal_year()

    items = [
        SpendingByFiscalYearItem(**record)
        for record in records
    ]

    return SpendingByFiscalYearResponse(
        count=len(items),
        data=items,
    )

def get_spending_by_department(
    *,
    fiscal_year: int | None = None,
    department: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> SpendingByDepartmentResponse:
    records = read_spending_by_department()

    if fiscal_year is not None:
        records = [
            record
            for record in records
            if record["fiscal_year"] == fiscal_year
        ]

    if department:
        department_query = department.casefold()

        records = [
            record
            for record in records
            if department_query
            in str(record["department"]).casefold()
        ]

    total_count = len(records)
    paginated_records = records[offset : offset + limit]

    items = [
        SpendingByDepartmentItem(**record)
        for record in paginated_records
    ]

    return SpendingByDepartmentResponse(
        total_count=total_count,
        count=len(items),
        limit=limit,
        offset=offset,
        data=items,
    )