import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.observability import ObservabilityMiddleware


client = TestClient(app)


def test_response_contains_request_id_header() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_response_contains_process_time_header() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Process-Time-MS" in response.headers
    assert float(response.headers["X-Process-Time-MS"]) >= 0


def test_client_request_id_is_preserved() -> None:
    request_id = "manual-test-001"

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_generated_request_ids_are_different() -> None:
    first_response = client.get("/health")
    second_response = client.get("/health")

    first_request_id = first_response.headers["X-Request-ID"]
    second_request_id = second_response.headers["X-Request-ID"]

    assert first_request_id != second_request_id

def test_successful_request_writes_structured_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(
        logging.INFO,
        logger="vendor_payments_api",
    ):
        response = client.get("/health")

    assert response.status_code == 200

    log_record = next(
        record
        for record in caplog.records
        if "api_request_completed" in record.getMessage()
    )

    log_data = json.loads(log_record.getMessage())

    assert log_data["event"] == "api_request_completed"
    assert log_data["request_id"] == response.headers["X-Request-ID"]
    assert log_data["method"] == "GET"
    assert log_data["path"] == "/health"
    assert log_data["status_code"] == 200
    assert log_data["process_time_ms"] >= 0


def test_unhandled_exception_writes_structured_error_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_app = FastAPI()
    test_app.add_middleware(ObservabilityMiddleware)

    @test_app.get("/raise-error")
    def raise_error() -> None:
        raise RuntimeError("Simulated middleware test error")

    test_client = TestClient(
        test_app,
        raise_server_exceptions=False,
    )

    with caplog.at_level(
        logging.ERROR,
        logger="vendor_payments_api",
    ):
        response = test_client.get(
            "/raise-error",
            headers={"X-Request-ID": "error-test-001"},
        )

    assert response.status_code == 500

    log_record = next(
        record
        for record in caplog.records
        if "api_request_error" in record.getMessage()
    )

    log_data = json.loads(log_record.getMessage())

    assert log_data["event"] == "api_request_error"
    assert log_data["request_id"] == "error-test-001"
    assert log_data["method"] == "GET"
    assert log_data["path"] == "/raise-error"
    assert log_data["process_time_ms"] >= 0