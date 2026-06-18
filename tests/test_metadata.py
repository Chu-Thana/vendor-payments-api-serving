from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_metadata_endpoint() -> None:
    response = client.get("/api/v1/metadata")

    assert response.status_code == 200
    assert response.json() == {
        "service": "Vendor Payments API",
        "version": "1.0.0",
        "batch_data_available": True,
        "streaming_data_available": True,
        "middleware_enabled": True,
        "request_id_enabled": True,
        "request_timing_enabled": True,
        "structured_logging_enabled": True,
        "cache_enabled": True,
    }