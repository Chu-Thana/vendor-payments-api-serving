from fastapi import APIRouter, HTTPException, Query

from app.models.batch import (
    FundCategorySummaryResponse,
    PendingByDepartmentResponse,
    SpendingByDepartmentResponse,
    SpendingByFiscalYearResponse,
    TopSuppliersResponse,
)

from app.services.batch_service import (
    get_fund_category_summary,
    get_pending_by_department,
    get_spending_by_department,
    get_spending_by_fiscal_year,
    get_top_suppliers,
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
    
@router.get(
    "/top-suppliers",
    response_model=TopSuppliersResponse,
    summary="Get top suppliers",
    responses={
        500: {"description": "Batch data file unavailable"},
    },
)
def read_top_suppliers_endpoint(
    supplier_name: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by supplier name",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of suppliers to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of suppliers to skip",
    ),
) -> TopSuppliersResponse:
    try:
        return get_top_suppliers(
            supplier_name=supplier_name,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Top suppliers data is unavailable",
        ) from exc  

@router.get(
    "/pending-by-department",
    response_model=PendingByDepartmentResponse,
    summary="Get pending payment summary by department",
    responses={
        500: {"description": "Batch data file unavailable"},
    },
)
def read_pending_by_department_endpoint(
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
) -> PendingByDepartmentResponse:
    try:
        return get_pending_by_department(
            fiscal_year=fiscal_year,
            department=department,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Pending by department data is unavailable",
        ) from exc
    

@router.get(
    "/fund-category-summary",
    response_model=FundCategorySummaryResponse,
    summary="Get fund category summary",
    responses={
        500: {"description": "Batch data file unavailable"},
    },
)
def read_fund_category_summary_endpoint(
    fiscal_year: int | None = Query(
        default=None,
        description="Filter by fiscal year",
    ),
    fund_type: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by fund type",
    ),
    fund_category: str | None = Query(
        default=None,
        min_length=1,
        description="Filter by fund category",
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
) -> FundCategorySummaryResponse:
    try:
        return get_fund_category_summary(
            fiscal_year=fiscal_year,
            fund_type=fund_type,
            fund_category=fund_category,
            limit=limit,
            offset=offset,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Fund category summary data is unavailable",
        ) from exc