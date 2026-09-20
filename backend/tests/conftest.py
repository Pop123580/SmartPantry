"""Test fixtures: the whole API runs against an in-memory SQLite database
(via FastAPI dependency override) — no Postgres or AWS required. Bedrock is
left unconfigured so recipe tests exercise the deterministic fallback.
"""

import os

# Environment MUST be set before importing the application.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-tests-only-0123456789abcdef"
os.environ.pop("JWT_SECRET", None)  # ensure the alias can never leak in
os.environ["BEDROCK_MODEL_ID"] = ""
os.environ["AWS_ACCESS_KEY_ID"] = ""
os.environ["AWS_SECRET_ACCESS_KEY"] = ""
os.environ["AWS_S3_BUCKET"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False
)


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_rows():
    """Full isolation between tests."""
    yield
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def register_user(client):
    def _register(email="ajay@example.com", name="Ajay", password="password123"):
        response = client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture()
def auth_headers(register_user):
    def _headers(email="ajay@example.com", name="Ajay"):
        body = register_user(email=email, name=name)
        return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]

    return _headers
