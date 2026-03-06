import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


class _DelayStub:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.calls = []

    def apply_async(self, args, headers):
        org_id, correlation_id = args
        self.calls.append((org_id, correlation_id, headers))
        return SimpleNamespace(id=self.job_id)


@pytest.fixture
def admin_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.admin as admin

    return reload(admin)


def _app_with_overrides(monkeypatch, admin, role: str, ctx_org_id: uuid.UUID):
    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1/admin")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=ctx_org_id, role=role)

    app.dependency_overrides[admin.get_current_user] = fake_user
    app.dependency_overrides[admin.get_db] = fake_db
    app.dependency_overrides[admin.get_org_context] = fake_ctx
    monkeypatch.setattr(admin, "get_org_context", fake_ctx)
    return app


def test_admin_recompute_enqueues_all_jobs(monkeypatch, admin_module):
    agg = _DelayStub("job-agg")
    fc = _DelayStub("job-forecast")
    alerts = _DelayStub("job-alerts")
    verify = _DelayStub("job-verify")

    monkeypatch.setattr(admin_module, "recompute_monthly_aggregates", agg)
    monkeypatch.setattr(admin_module, "recompute_forecasts", fc)
    monkeypatch.setattr(admin_module, "recompute_alerts", alerts)
    monkeypatch.setattr(admin_module, "verify_report_objects", verify)

    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)
    res = client.post(f"/api/v1/admin/recompute?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["jobs"]["monthly_aggregates"] == "job-agg"
    assert agg.calls and agg.calls[0][0] == str(org_id)
    assert "x-request-id" in agg.calls[0][2]


def test_admin_recompute_forbidden_if_not_owner(monkeypatch, admin_module):
    app = _app_with_overrides(monkeypatch, admin_module, "EDITOR", uuid.uuid4())
    client = TestClient(app)
    res = client.post(f"/api/v1/admin/recompute?org_id={uuid.uuid4()}")
    assert res.status_code == 403


def test_admin_recompute_tenant_isolation(monkeypatch, admin_module):
    agg = _DelayStub("job-agg")
    fc = _DelayStub("job-forecast")
    alerts = _DelayStub("job-alerts")
    verify = _DelayStub("job-verify")

    monkeypatch.setattr(admin_module, "recompute_monthly_aggregates", agg)
    monkeypatch.setattr(admin_module, "recompute_forecasts", fc)
    monkeypatch.setattr(admin_module, "recompute_alerts", alerts)
    monkeypatch.setattr(admin_module, "verify_report_objects", verify)

    requested_org = uuid.uuid4()
    context_org = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", context_org)
    client = TestClient(app)
    res = client.post(f"/api/v1/admin/recompute?org_id={requested_org}")
    assert res.status_code == 200
    assert agg.calls[0][0] == str(context_org)


def test_admin_recompute_forbidden_when_org_context_fails(monkeypatch, admin_module):
    app = FastAPI()
    app.include_router(admin_module.router, prefix="/api/v1/admin")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        raise HTTPException(status_code=403, detail="Forbidden")

    app.dependency_overrides[admin_module.get_current_user] = fake_user
    app.dependency_overrides[admin_module.get_db] = fake_db
    app.dependency_overrides[admin_module.get_org_context] = fake_ctx
    monkeypatch.setattr(admin_module, "get_org_context", fake_ctx)
    client = TestClient(app)
    res = client.post(f"/api/v1/admin/recompute?org_id={uuid.uuid4()}")
    assert res.status_code == 403
