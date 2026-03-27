import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeJobRepo:
    def __init__(self, db):
        self.db = db
        self.cancelled = None

    async def list_jobs(self, **kwargs):
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=kwargs["org_id"],
            task_id="task-1",
            task_name="recompute_alerts",
            dedupe_key="alerts:1",
            status="FAILED",
            progress=40,
            payload={"org_id": str(kwargs["org_id"])},
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

    async def by_id(self, job_id):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=job_id,
            org_id=self.org_id,
            task_id="task-1",
            task_name="recompute_alerts",
            payload={"org_id": str(self.org_id)},
            correlation_id="corr-1",
            created_at=now,
            updated_at=now,
        )

    async def mark_cancelled(self, task_id, *, error=None):
        self.cancelled = (task_id, error)


class FakeNotificationService:
    def __init__(self, repo):
        self.repo = repo

    async def create_org_notification(self, **kwargs):
        return None


class FakeAsyncResult:
    def __init__(self, task_id="new-task-1"):
        self.id = task_id


@pytest.fixture
def jobs_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.jobs as jobs

    return reload(jobs)


def _app_with_overrides(monkeypatch, jobs, org_id: uuid.UUID, repo: FakeJobRepo):
    app = FastAPI()
    app.include_router(jobs.router, prefix="/api/v1/jobs")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(*args, **kwargs):
        return SimpleNamespace(org_id=org_id, role="OWNER")

    repo.org_id = org_id
    app.dependency_overrides[jobs.get_current_user] = fake_user
    app.dependency_overrides[jobs.get_db] = fake_db
    monkeypatch.setattr(jobs, "get_org_context", fake_ctx)
    monkeypatch.setattr(jobs, "JobRepo", lambda db: repo)
    monkeypatch.setattr(jobs, "NotificationService", FakeNotificationService)
    monkeypatch.setattr(jobs, "_retry_task", lambda job: FakeAsyncResult())
    monkeypatch.setattr(jobs.celery_app.control, "revoke", lambda *args, **kwargs: None)
    return app


def test_jobs_retry_endpoint(monkeypatch, jobs_module):
    org_id = uuid.uuid4()
    repo = FakeJobRepo(object())
    client = TestClient(_app_with_overrides(monkeypatch, jobs_module, org_id, repo))

    res = client.post(f"/api/v1/jobs/{uuid.uuid4()}/retry?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["status"] == "REQUEUED"


def test_jobs_cancel_endpoint(monkeypatch, jobs_module):
    org_id = uuid.uuid4()
    repo = FakeJobRepo(object())
    client = TestClient(_app_with_overrides(monkeypatch, jobs_module, org_id, repo))

    res = client.post(f"/api/v1/jobs/{uuid.uuid4()}/cancel?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"
    assert repo.cancelled == ("task-1", "Cancelled by operator")
