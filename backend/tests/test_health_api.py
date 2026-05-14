from app.main import app
from fastapi.testclient import TestClient


def test_healthcheck() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_contains_core_paths() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert "/api/v1/auth/register" in payload["paths"]
    assert "/api/v1/runs" in payload["paths"]
