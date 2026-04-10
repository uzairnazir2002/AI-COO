from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings


def _health_client(monkeypatch: pytest.MonkeyPatch, *, auth_cookie_mode: str) -> TestClient:
    monkeypatch.setenv("SECRET_KEY", "test-health-secret-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("AUTH_COOKIE_MODE", auth_cookie_mode)
    get_settings.cache_clear()

    import app.api.v1.health as health_module

    class _FakeRedis:
        async def ping(self):
            return True

    monkeypatch.setattr(health_module, "redis_client", _FakeRedis())

    async def _override_get_db():
        class _Session:
            async def execute(self, *_a, **_k):
                return None

        yield _Session()

    app = FastAPI()
    app.include_router(health_module.router, prefix="/api/v1")
    # Must use the same get_db object the route registered with (not app.db.session after other tests patch it).
    app.dependency_overrides[health_module.get_db] = _override_get_db
    return TestClient(app)


@pytest.mark.parametrize(
    ("auth_cookie_mode", "expected_flag"),
    [
        ("true", True),
        ("false", False),
    ],
)
def test_health_reports_auth_cookie_mode(monkeypatch: pytest.MonkeyPatch, auth_cookie_mode: str, expected_flag: bool):
    client = _health_client(monkeypatch, auth_cookie_mode=auth_cookie_mode)
    try:
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert body["db"] is True
        assert body["redis"] is True
        assert body["auth_cookie_mode"] is expected_flag
        assert body["env"] == "development"
    finally:
        client.close()
        get_settings.cache_clear()
