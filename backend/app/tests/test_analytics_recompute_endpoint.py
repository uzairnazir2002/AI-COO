from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeJobRepo:
    def __init__(self, _db):
        self.pending_calls = []
        self.existing_job = None

    async def by_dedupe_key(self, _dedupe_key, _org_id=None):
        return self.existing_job

    async def upsert_pending(self, **kwargs):
        self.pending_calls.append(kwargs)
        return SimpleNamespace(task_id=kwargs["task_id"], status="PENDING")


class _FakeAuditRepo:
    def __init__(self, _db):
        self.actions = []

    async def log(self, _user_id, _org_id, action, _entity_type, _entity_id, _metadata):
        self.actions.append(action)


@pytest.fixture
def analytics_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.analytics as analytics

    return reload(analytics)


def _app_with_overrides(analytics_module, org_id: uuid.UUID, user_id: uuid.UUID):
    app = FastAPI()
    app.include_router(analytics_module.router, prefix="/api/v1/analytics")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=user_id, email="owner@example.com")

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[analytics_module.get_current_user] = fake_user
    app.dependency_overrides[analytics_module.get_db] = fake_db
    app.dependency_overrides[analytics_module.get_org_context] = fake_ctx
    analytics_module.get_org_context = fake_ctx
    return app


def test_analytics_recompute_enqueues_single_job(monkeypatch, analytics_module):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_job_repo = _FakeJobRepo(object())
    fake_audit_repo = _FakeAuditRepo(object())

    monkeypatch.setattr(analytics_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(analytics_module, "AuditRepo", lambda _db: fake_audit_repo)
    monkeypatch.setattr(
        analytics_module,
        "recompute_org_analytics",
        SimpleNamespace(apply_async=lambda args, headers=None: SimpleNamespace(id="analytics-job-1")),
    )

    app = _app_with_overrides(analytics_module, org_id, user_id)
    client = TestClient(app)
    res = client.post(f"/api/v1/analytics/recompute?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["job_id"] == "analytics-job-1"
    assert body["status"] == "PENDING"
    assert len(fake_job_repo.pending_calls) == 1
    assert "analytics.recompute.enqueue" in fake_audit_repo.actions


def test_analytics_recompute_reuses_active_job(monkeypatch, analytics_module):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_job_repo = _FakeJobRepo(object())
    fake_job_repo.existing_job = SimpleNamespace(
        task_id="analytics-job-running",
        status="RUNNING",
        result={"alerts_created": 1, "forecast_rows": 6},
    )

    monkeypatch.setattr(analytics_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(analytics_module, "AuditRepo", lambda _db: _FakeAuditRepo(object()))
    monkeypatch.setattr(
        analytics_module,
        "recompute_org_analytics",
        SimpleNamespace(apply_async=lambda args, headers=None: (_ for _ in ()).throw(AssertionError("apply_async should not run"))),
    )

    app = _app_with_overrides(analytics_module, org_id, user_id)
    client = TestClient(app)
    res = client.post(f"/api/v1/analytics/recompute?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["job_id"] == "analytics-job-running"
    assert body["status"] == "RUNNING"
    assert body["result"] == {"alerts_created": 1, "forecast_rows": 6}
