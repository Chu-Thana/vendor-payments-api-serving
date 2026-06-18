from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

import app.api.batch as batch_api
from app.cache.in_memory import InMemoryCache, api_response_cache
from app.cache.keys import build_cache_key
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_cache_between_tests() -> Generator[None, None, None]:
    api_response_cache.clear()

    yield

    api_response_cache.clear()


def test_in_memory_cache_returns_stored_value() -> None:
    cache = InMemoryCache()
    expected_value = {"count": 20}

    cache.set(
        key="test:key",
        value=expected_value,
        ttl_seconds=60,
    )

    assert cache.get("test:key") == expected_value
    assert cache.size() == 1


def test_expired_cache_entry_returns_none() -> None:
    cache = InMemoryCache()

    cache.set(
        key="test:expired",
        value={"status": "expired"},
        ttl_seconds=0,
    )

    assert cache.get("test:expired") is None
    assert cache.size() == 0


def test_cache_key_is_normalized_and_stable() -> None:
    cache_key = build_cache_key(
        "batch:test",
        limit=5,
        fiscal_year=None,
        department=" Public Health ",
    )

    assert cache_key == (
        "batch:test:"
        "department=public health:"
        "fiscal_year=all:"
        "limit=5"
    )


def test_identical_requests_return_miss_then_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service_call_count = 0
    original_service = batch_api.get_spending_by_fiscal_year

    def counted_service_call():
        nonlocal service_call_count
        service_call_count += 1
        return original_service()

    monkeypatch.setattr(
        batch_api,
        "get_spending_by_fiscal_year",
        counted_service_call,
    )

    first_response = client.get(
        "/api/v1/batch/spending-by-fiscal-year"
    )
    second_response = client.get(
        "/api/v1/batch/spending-by-fiscal-year"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert first_response.headers["X-Cache-Status"] == "MISS"
    assert second_response.headers["X-Cache-Status"] == "HIT"

    assert first_response.json() == second_response.json()
    assert service_call_count == 1

def test_different_query_parameters_create_separate_cache_entries() -> None:
    first_response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "fiscal_year": 2007,
            "limit": 5,
            "offset": 0,
        },
    )

    second_response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "fiscal_year": 2008,
            "limit": 5,
            "offset": 0,
        },
    )

    repeated_first_response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "fiscal_year": 2007,
            "limit": 5,
            "offset": 0,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert repeated_first_response.status_code == 200

    assert first_response.headers["X-Cache-Status"] == "MISS"
    assert second_response.headers["X-Cache-Status"] == "MISS"
    assert repeated_first_response.headers["X-Cache-Status"] == "HIT"

    assert api_response_cache.size() == 2

def test_invalid_request_is_not_cached() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-department",
        params={"limit": 0},
    )

    assert response.status_code == 422
    assert "X-Cache-Status" not in response.headers
    assert api_response_cache.size() == 0

def test_streaming_summary_returns_miss_then_hit() -> None:
    first_response = client.get("/api/v1/streaming/summary")
    second_response = client.get("/api/v1/streaming/summary")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.headers["X-Cache-Status"] == "MISS"
    assert second_response.headers["X-Cache-Status"] == "HIT"
    assert first_response.json() == second_response.json()

def test_streaming_query_parameters_create_separate_cache_entries() -> None:
    first_response = client.get(
        "/api/v1/streaming/events",
        params={
            "fiscal_year": 2021,
            "limit": 5,
            "offset": 0,
        },
    )

    second_response = client.get(
        "/api/v1/streaming/events",
        params={
            "fiscal_year": 2022,
            "limit": 5,
            "offset": 0,
        },
    )

    repeated_first_response = client.get(
        "/api/v1/streaming/events",
        params={
            "fiscal_year": 2021,
            "limit": 5,
            "offset": 0,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert repeated_first_response.status_code == 200

    assert first_response.headers["X-Cache-Status"] == "MISS"
    assert second_response.headers["X-Cache-Status"] == "MISS"
    assert repeated_first_response.headers["X-Cache-Status"] == "HIT"