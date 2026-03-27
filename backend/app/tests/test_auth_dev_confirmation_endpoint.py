from importlib import reload
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _stmt):
        return _FakeResult(self._rows)


def _build_app(module, rows):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/auth")

    async def fake_db():
        yield _FakeDb(rows)

    app.dependency_overrides[module.get_db] = fake_db
    return app


def test_dev_confirmation_token_returns_latest_token(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "development")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)
    rows = [
        SimpleNamespace(
            payload={
                "to": "other@example.com",
                "body": "Confirm your account with this token:\nother-token\n\nCall POST /api/v1/auth/confirm.",
            }
        ),
        SimpleNamespace(
            payload={
                "to": "owner@example.com",
                "body": "Confirm your account with this token:\nowner-token-123\n\nCall POST /api/v1/auth/confirm.",
            }
        ),
    ]

    client = TestClient(_build_app(auth_module, rows))
    res = client.get("/api/v1/auth/dev/confirmation-token?email=owner@example.com")
    assert res.status_code == 200
    body = res.json()
    assert body["found"] is True
    assert body["token"] == "owner-token-123"

    get_settings.cache_clear()


def test_dev_confirmation_token_hidden_outside_development(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "production")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)
    client = TestClient(_build_app(auth_module, []))
    res = client.get("/api/v1/auth/dev/confirmation-token?email=owner@example.com")
    assert res.status_code == 404

    get_settings.cache_clear()
