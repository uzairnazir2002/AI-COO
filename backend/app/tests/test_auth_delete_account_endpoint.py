from datetime import datetime, timezone
from importlib import reload
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/auth")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db_dep():
        yield _FakeDb()

    async def fake_user():
        return SimpleNamespace(id=uuid4(), email="owner@example.com", is_active=True)

    app.dependency_overrides[module.get_db] = fake_db_dep
    app.dependency_overrides[module.get_current_user] = fake_user
    return app


def test_delete_account_creates_request(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    class _FakePrivacyService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def request_account_deletion(self, *, user_id, reason):
            _ = (user_id, reason)
            return {"request_id": uuid4(), "delete_after": "2026-04-01T00:00:00Z"}

    monkeypatch.setattr(auth_module, "PrivacyService", _FakePrivacyService)
    app = _build_app(auth_module)
    client = TestClient(app)
    res = client.post("/api/v1/auth/delete-account", json={"reason": "No longer needed"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["request_id"]


def test_list_delete_account_requests(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    now = datetime.now(timezone.utc)
    request_id = uuid4()
    user_id = uuid4()

    class _FakePrivacyService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def list_account_deletion_requests(self, *, user_id, limit):
            _ = (user_id, limit)
            return [
                SimpleNamespace(
                    id=request_id,
                    scope="USER",
                    status="PENDING",
                    requested_by_user_id=user_id,
                    target_user_id=user_id,
                    target_org_id=None,
                    reason="cleanup",
                    delete_after=now,
                    processed_at=None,
                    created_at=now,
                    updated_at=now,
                )
            ]

    monkeypatch.setattr(auth_module, "PrivacyService", _FakePrivacyService)
    app = _build_app(auth_module)
    client = TestClient(app)
    res = client.get("/api/v1/auth/delete-account/requests?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(request_id)
    assert body["items"][0]["status"] == "PENDING"
