from app.models.batch import (
    SpendingByFiscalYearItem,
    SpendingByFiscalYearResponse,
)
from app.repositories.batch_repository import (
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