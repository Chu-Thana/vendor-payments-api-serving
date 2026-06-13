from fastapi import APIRouter

from app.models.common import HealthResponse


router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API health",
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="vendor-payments-api",
    )