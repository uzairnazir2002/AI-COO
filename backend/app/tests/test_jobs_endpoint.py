import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient


class FakeRepo:
    def __init__(self, db):
        self.db = db
        self.args = None

    async def list_jobs(self, **kwargs):
        self.args = kwargs
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=kwargs["org_id"],
            task_id="task-1",
            task_name="recalc_alerts",
            dedupe_key="alerts:1",
            status="FAILED",
            progress=40,
            payload={"a": 1},
            result=None,
            request_id="req-1",
            correlation_id="corr-1",
            last_error="boom",
            traceback_summary="stack",
            retry_count=2,
            last_retry_at=now,
            created_at=now,
            updated_at=now,
        )
        return [item], 1


@pytest.fixture
def jobs_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.jobs as jobs

    return reload(jobs)


def _app_with_overrides(monkeypatch, jobs, role: str, ctx_org_id: uuid.UUID):
    app = FastAPI()
    app.include_router(jobs.router, prefix="/api/v1/jobs")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(*args, **kwargs):
        return SimpleNamespace(org_id=ctx_org_id, role=role)

    app.dependency_overrides[jobs.get_current_user] = fake_user
    app.dependency_overrides[jobs.get_db] = fake_db
    monkeypatch.setattr(jobs, "get_org_context", fake_ctx)
    return app


def test_jobs_endpoint_viewer_redacts_sensitive_fields(monkeypatch, jobs_module):
    repo = FakeRepo(object())
    monkeypatch.setattr(jobs_module, "JobRepo", lambda db: repo)

    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, jobs_module, "VIEWER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/jobs?org_id={org_id}")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] == 1
    assert payload["items"][0]["last_error"] is None
    assert payload["items"][0]["traceback_summary"] is None


def test_jobs_endpoint_uses_context_org_for_tenant_scoping(monkeypatch, jobs_module):
    repo = FakeRepo(object())
    monkeypatch.setattr(jobs_module, "JobRepo", lambda db: repo)

    requested_org = uuid.uuid4()
    context_org = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, jobs_module, "OWNER", context_org)
    client = TestClient(app)

    res = client.get(f"/api/v1/jobs?org_id={requested_org}")
    assert res.status_code == 200
    assert repo.args["org_id"] == context_org


def test_jobs_endpoint_forbidden_when_org_context_fails(monkeypatch, jobs_module):
    repo = FakeRepo(object())
    monkeypatch.setattr(jobs_module, "JobRepo", lambda db: repo)

    app = FastAPI()
    app.include_router(jobs_module.router, prefix="/api/v1/jobs")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    async def fake_db():
        yield object()

    async def fake_ctx(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    app.dependency_overrides[jobs_module.get_current_user] = fake_user
    app.dependency_overrides[jobs_module.get_db] = fake_db
    monkeypatch.setattr(jobs_module, "get_org_context", fake_ctx)

    client = TestClient(app)
    res = client.get(f"/api/v1/jobs?org_id={uuid.uuid4()}")
    assert res.status_code == 403
