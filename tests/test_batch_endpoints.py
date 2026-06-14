from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_spending_by_fiscal_year_endpoint() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-fiscal-year"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["count"] == 20
    assert len(body["data"]) == 20

    first_item = body["data"][0]

    assert first_item["fiscal_year"] == 2007
    assert first_item["record_count"] == 164694
    assert first_item["unique_suppliers"] == 47970

def test_spending_by_department_pagination() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 1121
    assert body["count"] == 5
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(body["data"]) == 5


def test_spending_by_department_fiscal_year_filter() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "fiscal_year": 2007,
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 57
    assert body["count"] == 5

    assert all(
        item["fiscal_year"] == 2007
        for item in body["data"]
    )


def test_spending_by_department_name_filter() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "department": "Public Health",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 20
    assert body["count"] == 5

    assert all(
        "public health" in item["department"].casefold()
        for item in body["data"]
    )


def test_spending_by_department_invalid_pagination() -> None:
    response = client.get(
        "/api/v1/batch/spending-by-department",
        params={
            "limit": 0,
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_top_suppliers_pagination() -> None:
    response = client.get(
        "/api/v1/batch/top-suppliers",
        params={
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 100
    assert body["count"] == 5
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(body["data"]) == 5

    assert (
        body["data"][0]["supplier_name"]
        == "THE DEPOSITORY TRUST COMPANY"
    )


def test_top_suppliers_name_filter() -> None:
    response = client.get(
        "/api/v1/batch/top-suppliers",
        params={
            "supplier_name": "BANK",
            "limit": 10,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 12
    assert body["count"] == 10

    assert all(
        "bank" in item["supplier_name"].casefold()
        for item in body["data"]
    )


def test_top_suppliers_offset() -> None:
    first_response = client.get(
        "/api/v1/batch/top-suppliers",
        params={
            "limit": 5,
            "offset": 0,
        },
    )
    second_response = client.get(
        "/api/v1/batch/top-suppliers",
        params={
            "limit": 5,
            "offset": 5,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_body = first_response.json()
    second_body = second_response.json()

    assert second_body["offset"] == 5
    assert second_body["count"] == 5

    assert (
        first_body["data"][0]["supplier_name"]
        != second_body["data"][0]["supplier_name"]
    )


def test_top_suppliers_invalid_pagination() -> None:
    response = client.get(
        "/api/v1/batch/top-suppliers",
        params={
            "limit": 0,
            "offset": -1,
        },
    )

    assert response.status_code == 422

def test_pending_by_department_pagination() -> None:
    response = client.get(
        "/api/v1/batch/pending-by-department",
        params={
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 643
    assert body["count"] == 5
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert len(body["data"]) == 5


def test_pending_by_department_fiscal_year_filter() -> None:
    response = client.get(
        "/api/v1/batch/pending-by-department",
        params={
            "fiscal_year": 2007,
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 54
    assert body["count"] == 5

    assert all(
        item["fiscal_year"] == 2007
        for item in body["data"]
    )


def test_pending_by_department_name_filter() -> None:
    response = client.get(
        "/api/v1/batch/pending-by-department",
        params={
            "department": "Public Health",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 18
    assert body["count"] == 5

    assert all(
        "public health" in item["department"].casefold()
        for item in body["data"]
    )


def test_pending_by_department_combined_filters() -> None:
    response = client.get(
        "/api/v1/batch/pending-by-department",
        params={
            "fiscal_year": 2007,
            "department": "Public Health",
            "limit": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_count"] == 1
    assert body["count"] == 1
    assert body["data"][0]["fiscal_year"] == 2007
    assert body["data"][0]["department"] == "DPH Public Health"


def test_pending_by_department_invalid_pagination() -> None:
    response = client.get(
        "/api/v1/batch/pending-by-department",
        params={
            "limit": 0,
            "offset": -1,
        },
    )

    assert response.status_code == 422