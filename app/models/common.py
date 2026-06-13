from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class MetadataResponse(BaseModel):
    service: str
    version: str
    batch_data_available: bool
    streaming_data_available: bool