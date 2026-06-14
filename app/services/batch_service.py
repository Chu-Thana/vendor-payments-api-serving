from app.models.batch import (
    PendingByDepartmentItem,
    PendingByDepartmentResponse,
    SpendingByDepartmentItem,
    SpendingByDepartmentResponse,
    SpendingByFiscalYearItem,
    SpendingByFiscalYearResponse,
    TopSupplierItem,
    TopSuppliersResponse,
)

from app.repositories.batch_repository import (
    read_pending_by_department,
    read_spending_by_department,
    read_spending_by_fiscal_year,
    read_top_suppliers,
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

def get_top_suppliers(
    *,
    supplier_name: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> TopSuppliersResponse:
    records = read_top_suppliers()

    if supplier_name:
        supplier_query = supplier_name.casefold()

        records = [
            record
            for record in records
            if supplier_query
            in str(record["supplier_name"]).casefold()
        ]

    total_count = len(records)
    paginated_records = records[offset : offset + limit]

    items = [
        TopSupplierItem(**record)
        for record in paginated_records
    ]

    return TopSuppliersResponse(
        total_count=total_count,
        count=len(items),
        limit=limit,
        offset=offset,
        data=items,
    )

def get_pending_by_department(
    *,
    fiscal_year: int | None = None,
    department: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> PendingByDepartmentResponse:
    records = read_pending_by_department()

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
        PendingByDepartmentItem(**record)
        for record in paginated_records
    ]

    return PendingByDepartmentResponse(
        total_count=total_count,
        count=len(items),
        limit=limit,
        offset=offset,
        data=items,
    )