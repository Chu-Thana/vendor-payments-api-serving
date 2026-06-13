from fastapi import APIRouter

from app.models.common import MetadataResponse


router = APIRouter(
    prefix="/api/v1",
    tags=["Metadata"],
)


@router.get(
    "/metadata",
    response_model=MetadataResponse,
    summary="Get API metadata",
)
def get_metadata() -> MetadataResponse:
    return MetadataResponse(
        service="Vendor Payments API",
        version="1.0.0",
        batch_data_available=True,
        streaming_data_available=True,
    )