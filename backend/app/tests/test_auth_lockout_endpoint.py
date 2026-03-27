from importlib import reload
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/auth")

    class _FakeDb:
        def __init__(self):
            self.commits = 0

        async def commit(self):
            self.commits += 1

    fake_db = _FakeDb()

    async def fake_db_dep():
        yield fake_db

    async def fake_user():
        return SimpleNamespace(id=uuid4(), email="owner@example.com", is_active=True)

    app.dependency_overrides[module.get_db] = fake_db_dep
    app.dependency_overrides[module.get_current_user] = fake_user
    return app, fake_db


def test_login_rejects_when_lockout_is_active(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    async def _noop_rate_limit(*_args, **_kwargs):
        return None

    async def _locked(*_args, **_kwargs):
        return SimpleNamespace(locked=True, remaining_seconds=30, failure_count=0, escalation_level=1, escalated=False)

    class _FakeAuditRepo:
        def __init__(self, _db):
            pass

        async def log(self, *args, **kwargs):
            _ = (args, kwargs)

    monkeypatch.setattr(auth_module, "enforce_auth_rate_limit", _noop_rate_limit)
    monkeypatch.setattr(auth_module, "is_locked", _locked)
    monkeypatch.setattr(auth_module, "AuditRepo", _FakeAuditRepo)

    app, _ = _build_app(auth_module)
    client = TestClient(app)
    res = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "Password123!"})
    assert res.status_code == 429

    get_settings.cache_clear()


def test_login_records_failure_and_returns_unauthorized(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from app.core.config import get_settings
    from app.domain.services.errors import UnauthorizedError

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    async def _noop_rate_limit(*_args, **_kwargs):
        return None

    async def _unlocked(*_args, **_kwargs):
        return SimpleNamespace(locked=False, remaining_seconds=0, failure_count=0, escalation_level=0, escalated=False)

    async def _record_failure(*_args, **_kwargs):
        return SimpleNamespace(locked=False, remaining_seconds=0, failure_count=1, escalation_level=0, escalated=False)

    async def _clear(*_args, **_kwargs):
        return None

    class _FakeAuditRepo:
        actions = []

        def __init__(self, _db):
            pass

        async def log(self, _user_id, _org_id, action, _entity_type, _entity_id, _metadata):
            type(self).actions.append(action)

    class _FakeAuthService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def login(self, *_args, **_kwargs):
            raise UnauthorizedError("Invalid credentials")

    monkeypatch.setattr(auth_module, "enforce_auth_rate_limit", _noop_rate_limit)
    monkeypatch.setattr(auth_module, "is_locked", _unlocked)
    monkeypatch.setattr(auth_module, "record_login_failure", _record_failure)
    monkeypatch.setattr(auth_module, "clear_login_failures", _clear)
    monkeypatch.setattr(auth_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(auth_module, "AuthService", _FakeAuthService)

    app, _ = _build_app(auth_module)
    client = TestClient(app)
    res = client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "WrongPass123!"})
    assert res.status_code == 401
    assert "auth.login.failed" in _FakeAuditRepo.actions

    get_settings.cache_clear()
