from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.middleware import RequestContextMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


def test_https_enforcement_blocks_plain_http(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENFORCE_HTTPS", "true")
    get_settings.cache_clear()

    client = TestClient(_app())
    res = client.get("/ping")
    assert res.status_code == 400
    assert res.json()["detail"] == "HTTPS is required"

    get_settings.cache_clear()


def test_https_enforcement_allows_forwarded_https(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ENFORCE_HTTPS", "true")
    get_settings.cache_clear()

    client = TestClient(_app())
    res = client.get("/ping", headers={"x-forwarded-proto": "https"})
    assert res.status_code == 200
    assert res.json()["ok"] is True

    get_settings.cache_clear()
