from fastapi import APIRouter, HTTPException, Query

from app.models.batch import (
    SpendingByDepartmentResponse,
    SpendingByFiscalYearResponse,
)
from app.services.batch_service import (
    get_spending_by_department,
    get_spending_by_fiscal_year,
)


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

@router.get(
    "/spending-by-department",
    response_model=SpendingByDepartmentResponse,
    summary="Get spending summary by department",
    responses={
        500: {"description": "Batch data file unavailable"},
    },
)
def read_spending_by_department_endpoint(
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
        description="Maximum number of records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip",
    ),
) -> SpendingByDepartmentResponse:
    try:
        return get_spending_by_department(
            fiscal_year=fiscal_year,
            department=department,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Spending by department data is unavailable",
        ) from exc