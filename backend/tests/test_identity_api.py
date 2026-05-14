from collections.abc import Iterator

import app.db.base  # noqa: F401
import pytest
from app.db.base_class import Base
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_auth_responses_include_profile_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    user = response.json()["user"]
    assert user == {
        "id": 1,
        "email": "user@example.com",
        "full_name": None,
        "company": None,
        "role": None,
        "description": None,
    }


def test_user_can_update_and_read_profile_fields(client: TestClient) -> None:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password123"},
    )
    access_token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    update_response = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "Ivan Petrov",
            "company": "ACME Manufacturing",
            "role": "Process Engineer",
            "description": "Works with CNC routing scenarios.",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json() == {
        "id": 1,
        "email": "user@example.com",
        "full_name": "Ivan Petrov",
        "company": "ACME Manufacturing",
        "role": "Process Engineer",
        "description": "Works with CNC routing scenarios.",
    }

    me_response = client.get("/api/v1/users/me", headers=headers)

    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Ivan Petrov"
    assert me_response.json()["company"] == "ACME Manufacturing"
