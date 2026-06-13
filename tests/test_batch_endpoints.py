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