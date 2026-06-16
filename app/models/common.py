from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class MetadataResponse(BaseModel):
    service: str
    version: str
    batch_data_available: bool
    streaming_data_available: bool
    middleware_enabled: bool
    request_id_enabled: bool
    request_timing_enabled: bool
    structured_logging_enabled: bool
    cache_enabled: bool