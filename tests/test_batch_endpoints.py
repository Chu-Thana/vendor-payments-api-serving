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