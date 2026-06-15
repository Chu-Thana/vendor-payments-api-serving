from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_streaming_events_pagination() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 1000
    assert body["count"] == 5
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(body["data"]) == 5

    assert (
        body["data"][0]["event_id"]
        == "4fdec289-f11b-428a-b82f-4dd4d4dbd012"
    )


def test_streaming_events_fiscal_year_filter() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "fiscal_year": 2021,
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 70
    assert body["count"] == 5

    assert all(
        item["fiscal_year"] == 2021
        for item in body["data"]
    )


def test_streaming_events_supplier_filter() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "supplier_name": "ERIE",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 2
    assert body["count"] == 2

    assert all(
        "erie" in item["supplier_name"].casefold()
        for item in body["data"]
    )


def test_streaming_events_dedup_status_filter() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "dedup_status": "accepted",
            "limit": 5,
            "offset": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 1000
    assert body["count"] == 5
    assert body["offset"] == 5

    assert all(
        item["dedup_status"] == "accepted"
        for item in body["data"]
    )


def test_streaming_events_combined_filters() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "fiscal_year": 2021,
            "supplier_name": "ERIE",
            "dedup_status": "accepted",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] >= 1

    assert all(
        item["fiscal_year"] == 2021
        and "erie" in item["supplier_name"].casefold()
        and item["dedup_status"] == "accepted"
        for item in body["data"]
    )


def test_streaming_events_invalid_pagination() -> None:
    response = client.get(
        "/api/v1/streaming/events",
        params={
            "limit": 0,
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_streaming_summary_endpoint() -> None:
    response = client.get(
        "/api/v1/streaming/summary",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_events"] == 1000
    assert body["total_payment_amount"] == 3275248584.18
    assert body["unique_departments"] == 56
    assert body["unique_suppliers"] == 600
    assert body["minimum_fiscal_year"] == 2007
    assert body["maximum_fiscal_year"] == 2026


def test_streaming_summary_fiscal_year_counts() -> None:
    response = client.get(
        "/api/v1/streaming/summary",
    )

    assert response.status_code == 200

    body = response.json()
    year_counts = {
        item["fiscal_year"]: item["event_count"]
        for item in body["events_by_fiscal_year"]
    }

    assert len(year_counts) == 20
    assert year_counts[2007] == 21
    assert year_counts[2021] == 70
    assert year_counts[2026] == 77
    assert sum(year_counts.values()) == 1000


def test_streaming_summary_dedup_counts() -> None:
    response = client.get(
        "/api/v1/streaming/summary",
    )

    assert response.status_code == 200

    body = response.json()

    assert body["events_by_dedup_status"] == [
        {
            "dedup_status": "accepted",
            "event_count": 1000,
        }
    ]