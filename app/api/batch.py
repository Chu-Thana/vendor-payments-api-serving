from fastapi import APIRouter, HTTPException

from app.models.batch import SpendingByFiscalYearResponse
from app.services.batch_service import get_spending_by_fiscal_year


router = APIRouter(
    prefix="/api/v1/batch",
    tags=["Batch Analytics"],
)


@router.get(
    "/spending-by-fiscal-year",
    response_model=SpendingByFiscalYearResponse,
    summary="Get spending summary by fiscal year",
    responses={
        500: {"description": "Batch data file unavailable"},
    },
)
def read_spending_by_fiscal_year() -> SpendingByFiscalYearResponse:
    try:
        return get_spending_by_fiscal_year()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Spending by fiscal year data is unavailable",
        ) from exc