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


def test_mfa_enable_and_regenerate_return_recovery_codes(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    class _FakeAuthService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def enable_mfa(self, *, user_id, code):
            _ = (user_id, code)
            return ["AB12CD34", "EF56GH78"]

        async def regenerate_recovery_codes(self, *, user_id, password, code):
            _ = (user_id, password, code)
            return ["ZX90CV12"]

    async def _noop_rate_limit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(auth_module, "AuthService", _FakeAuthService)
    monkeypatch.setattr(auth_module, "enforce_auth_rate_limit", _noop_rate_limit)

    app, fake_db = _build_app(auth_module)
    client = TestClient(app)

    enable = client.post("/api/v1/auth/mfa/enable", json={"code": "123456"})
    assert enable.status_code == 200
    assert enable.json()["recovery_codes"] == ["AB12CD34", "EF56GH78"]

    regenerate = client.post(
        "/api/v1/auth/mfa/recovery-codes/regenerate",
        json={"password": "Password123!", "code": "123456"},
    )
    assert regenerate.status_code == 200
    assert regenerate.json()["recovery_codes"] == ["ZX90CV12"]
    assert fake_db.commits == 2

    get_settings.cache_clear()


def test_login_passes_mfa_recovery_code_to_service(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)
    captured = {"mfa_recovery_code": None}

    class _FakeAuthService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def login(self, email, password, request, mfa_code=None, mfa_recovery_code=None):
            _ = (email, password, request, mfa_code)
            captured["mfa_recovery_code"] = mfa_recovery_code
            return SimpleNamespace(access_token="a", refresh_token="r", token_type="bearer", expires_in=900)

    async def _noop_rate_limit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(auth_module, "AuthService", _FakeAuthService)
    monkeypatch.setattr(auth_module, "enforce_auth_rate_limit", _noop_rate_limit)

    app, _ = _build_app(auth_module)
    client = TestClient(app)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "Password123!", "mfa_recovery_code": "AB12CD34"},
    )
    assert response.status_code == 200
    assert captured["mfa_recovery_code"] == "AB12CD34"

    get_settings.cache_clear()


def test_sessions_endpoint_forwards_refresh_token_to_service(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)
    captured = {"refresh": None}

    class _FakeAuthService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def list_sessions(self, *, user_id, current_refresh_token):
            _ = user_id
            captured["refresh"] = current_refresh_token
            return [
                {
                    "id": uuid4(),
                    "created_at": "2026-03-24T00:00:00Z",
                    "expires_at": "2026-03-25T00:00:00Z",
                    "last_used_at": None,
                    "user_agent": "pytest",
                    "ip_address": "127.0.0.1",
                    "is_revoked": False,
                    "is_current": True,
                }
            ]

    monkeypatch.setattr(auth_module, "AuthService", _FakeAuthService)

    app, _ = _build_app(auth_module)
    client = TestClient(app)

    response = client.get("/api/v1/auth/sessions?refresh_token=abc")
    assert response.status_code == 200
    assert captured["refresh"] == "abc"
    assert len(response.json()["items"]) == 1

    get_settings.cache_clear()


def test_reauth_returns_token(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    from app.core.config import get_settings

    get_settings.cache_clear()
    import app.api.v1.auth as auth_module

    auth_module = reload(auth_module)

    class _FakeAuthService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def authenticate_for_reauth(self, *, user_id, password, mfa_code, mfa_recovery_code):
            _ = (user_id, password, mfa_code, mfa_recovery_code)
            return None

    class _FakeOrgRepo:
        def __init__(self, _db):
            pass

        async def get_settings(self, _org_id):
            return SimpleNamespace(sensitive_action_reauth_minutes=25)

    class _FakeAuditRepo:
        def __init__(self, _db):
            pass

        async def log(self, *args, **kwargs):
            _ = (args, kwargs)

    async def _noop_rate_limit(*_args, **_kwargs):
        return None

    async def _fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    monkeypatch.setattr(auth_module, "AuthService", _FakeAuthService)
    monkeypatch.setattr(auth_module, "OrgRepo", _FakeOrgRepo)
    monkeypatch.setattr(auth_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(auth_module, "enforce_auth_rate_limit", _noop_rate_limit)
    monkeypatch.setattr(auth_module, "get_org_context", _fake_ctx)

    app, _ = _build_app(auth_module)
    client = TestClient(app)
    org_id = uuid4()

    response = client.post(
        f"/api/v1/auth/reauth?org_id={org_id}",
        json={"password": "Password123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["token_type"] == "reauth"
    assert body["expires_in"] == 1500
    assert isinstance(body["token"], str) and len(body["token"]) > 10

    get_settings.cache_clear()
