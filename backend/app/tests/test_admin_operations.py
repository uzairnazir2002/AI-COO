import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeOutboxRepo:
    def __init__(self, db):
        self.db = db
        self.args = None
        self.last_requeued = None

    async def list_events(self, **kwargs):
        self.args = kwargs
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=kwargs["org_id"],
            event_type="email.send",
            payload={"to": "owner@example.com", "subject": "s"},
            status="RETRYING",
            attempts=2,
            max_attempts=5,
            available_at=now,
            sent_at=None,
            last_error="smtp down",
            correlation_id="corr-1",
            dedupe_key="invite-1",
            created_at=now,
        )
        return [item], 1

    async def by_id(self, event_id):
        now = datetime.now(timezone.utc)
        org_id = self.args["org_id"] if self.args else uuid.uuid4()
        return SimpleNamespace(
            id=event_id,
            org_id=org_id,
            status="FAILED",
            attempts=2,
            max_attempts=5,
            available_at=now,
            sent_at=None,
            last_error="smtp down",
        )

    async def requeue(self, event, *, reset_attempts: bool = False):
        self.last_requeued = (event.id, reset_attempts)
        event.status = "PENDING"
        if reset_attempts:
            event.attempts = 0
        return event

    async def counts_by_status(self, *, org_id):
        assert org_id
        return {"PENDING": 1, "RETRYING": 2}


class FakeJobRepo:
    def __init__(self, db):
        self.db = db

    async def list_system_jobs(self, **kwargs):
        now = datetime.now(timezone.utc)
        item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=None,
            task_id="task-1",
            task_name="process_outbox",
            dedupe_key="outbox:100",
            status="SUCCEEDED",
            progress=100,
            payload={"batch_size": 100},
            result={"processed": 5},
            request_id=None,
            correlation_id=None,
            last_error=None,
            traceback_summary=None,
            retry_count=0,
            last_retry_at=None,
            created_at=now,
            updated_at=now,
        )
        return [item], 1


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

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=ctx_org_id, role=role)

    app.dependency_overrides[admin.get_current_user] = fake_user
    app.dependency_overrides[admin.get_db] = fake_db
    app.dependency_overrides[admin.get_org_context] = fake_ctx
    monkeypatch.setattr(admin, "get_org_context", fake_ctx)
    return app


def test_admin_outbox_endpoint(monkeypatch, admin_module):
    monkeypatch.setattr(admin_module, "OutboxRepo", FakeOutboxRepo)
    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/outbox?org_id={org_id}&status=RETRYING")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["counts_by_status"]["RETRYING"] == 2
    assert body["items"][0]["event_type"] == "email.send"


def test_admin_system_status_endpoint(monkeypatch, admin_module):
    monkeypatch.setattr(admin_module, "OutboxRepo", FakeOutboxRepo)
    monkeypatch.setattr(admin_module, "JobRepo", FakeJobRepo)
    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/system-status?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["system_job_total"] == 1
    assert any(item["name"] == "outbox-consumer" for item in body["scheduler"])
    assert body["system_jobs"][0]["task_name"] == "process_outbox"


def test_admin_outbox_retry_endpoint(monkeypatch, admin_module):
    fake_repo = FakeOutboxRepo(None)
    monkeypatch.setattr(admin_module, "OutboxRepo", lambda db: fake_repo)
    org_id = uuid.uuid4()
    fake_repo.args = {"org_id": org_id}
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    event_id = uuid.uuid4()
    res = client.post(f"/api/v1/admin/outbox/{event_id}/retry?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["status"] == "PENDING"
