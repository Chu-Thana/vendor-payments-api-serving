from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_health_check():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Project 2 API is running"}

def test_docs_available():
    response = client.get("/docs")

    assert response.status_code == 200