import uuid
import hashlib
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

    async def count_active(self, org_id):
        assert org_id
        return 3

    async def oldest_active_created_at(self, _org_id):
        return datetime.now(timezone.utc)

    async def by_id(self, job_id):
        return SimpleNamespace(
            id=job_id,
            org_id=self.db.org_id if hasattr(self.db, "org_id") else uuid.uuid4(),
            task_name="recompute_alerts",
            payload={
                "org_id": (str(self.db.org_id) if hasattr(self.db, "org_id") else str(uuid.uuid4()))
            },
            correlation_id="corr-1",
        )


class FakeDeadLetterRepo:
    def __init__(self, db):
        self.db = db
        self.item = None

    async def open_count(self, *, org_id):
        assert org_id
        return 2

    async def list_events(self, **kwargs):
        now = datetime.now(timezone.utc)
        self.item = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=kwargs["org_id"],
            source_type="OUTBOX",
            source_id=uuid.uuid4(),
            source_task_id=None,
            source_name="email.send",
            status="OPEN",
            attempts=5,
            last_error="smtp timeout",
            payload={"to": "owner@example.com"},
            metadata_json={},
            first_failed_at=now,
            last_failed_at=now,
            replayed_at=None,
            created_at=now,
            updated_at=now,
        )
        return [self.item], 1

    async def counts_by_status(self, *, org_id):
        assert org_id
        return {"OPEN": 1}

    async def by_id(self, dead_letter_id):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=dead_letter_id,
            org_id=self.db.org_id if hasattr(self.db, "org_id") else uuid.uuid4(),
            source_type="OUTBOX",
            source_id=uuid.uuid4(),
            source_task_id=None,
            source_name="email.send",
            status="OPEN",
            attempts=5,
            last_error="smtp timeout",
            payload={},
            metadata_json={},
            first_failed_at=now,
            last_failed_at=now,
            replayed_at=None,
            created_at=now,
            updated_at=now,
        )

    async def mark_replayed(self, event, *, metadata_json=None):
        event.status = "REPLAYED"
        return event

    async def mark_dismissed(self, event, *, reason=None):
        _ = reason
        event.status = "DISMISSED"
        return event


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
        org_id = ctx_org_id

        async def commit(self):
            return None

        async def scalar(self, *_args, **_kwargs):
            return 11

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


def test_admin_runtime_metrics_endpoint(monkeypatch, admin_module):
    monkeypatch.setattr(admin_module, "OutboxRepo", FakeOutboxRepo)
    monkeypatch.setattr(admin_module, "JobRepo", FakeJobRepo)
    monkeypatch.setattr(admin_module, "DeadLetterRepo", FakeDeadLetterRepo)
    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/runtime-metrics?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["queue_depth_active"] == 3
    assert "queue_lag_seconds" in body
    assert body["queue_lag_breach"] is False
    assert body["outbox_pending"] == 3
    assert body["dead_letter_open"] == 2
    assert body["worker_health"] == "degraded"
    assert body["db_active_connections"] == 11
    assert "auth_lockout_failures_total" in body
    assert "auth_lockouts_total" in body
    assert "auth_lockout_escalations_total" in body


def test_admin_runtime_slos_endpoint(monkeypatch, admin_module):
    org_id = uuid.uuid4()
    monkeypatch.setattr(
        admin_module,
        "runtime_slo_snapshot",
        lambda **_kwargs: {
            "window_seconds": 300,
            "p95_threshold_ms": 2000.0,
            "error_rate_threshold_pct": 1.0,
            "total_requests": 25,
            "endpoints": [
                {
                    "endpoint": "GET /api/v1/analytics/summary",
                    "requests": 10,
                    "p95_ms": 850.0,
                    "error_rate_pct": 0.0,
                    "breach": False,
                }
            ],
        },
    )
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/runtime-slos?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["total_requests"] == 25
    assert body["endpoints"][0]["endpoint"] == "GET /api/v1/analytics/summary"


def test_admin_audit_export_endpoint(monkeypatch, admin_module):
    org_id = uuid.uuid4()

    class _FakeAuditRepo:
        def __init__(self, _db):
            pass

        async def list_export_events(self, **_kwargs):
            now = datetime.now(timezone.utc)
            return [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    created_at=now,
                    actor_user_id=uuid.uuid4(),
                    org_id=org_id,
                    action="auth.login",
                    entity_type="user",
                    entity_id="u1",
                    metadata_json={"ok": True},
                )
            ]

    monkeypatch.setattr(admin_module, "AuditRepo", _FakeAuditRepo)
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/audit/export?org_id={org_id}")
    assert res.status_code == 200
    assert res.headers.get("X-Audit-Checksum-SHA256")
    assert res.headers.get("X-Audit-Event-Count") == "1"
    assert "auth.login" in res.text
    canonical = "\n".join([line for line in res.text.splitlines() if line])
    expected_checksum = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert res.headers.get("X-Audit-Checksum-SHA256") == expected_checksum


def test_admin_rotate_org_pii_endpoint(monkeypatch, admin_module):
    org_id = uuid.uuid4()

    class _FakePrivacyService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def rotate_org_pii(self, *, actor_user_id, org_id):
            _ = (actor_user_id, org_id)
            return {"rotated_fields": 3, "active_key_id": "primary"}

    monkeypatch.setattr(admin_module, "PrivacyService", _FakePrivacyService)
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)
    res = client.post(f"/api/v1/admin/security/rotate-pii?org_id={org_id}")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["rotated_fields"] == 3


def test_admin_deletion_requests_endpoint(monkeypatch, admin_module):
    org_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    request_id = uuid.uuid4()

    class _FakePrivacyService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def list_org_deletion_requests(self, *, actor_user_id, org_id, limit):
            _ = (actor_user_id, org_id, limit)
            return [
                SimpleNamespace(
                    id=request_id,
                    scope="ORG",
                    status="PENDING",
                    requested_by_user_id=uuid.uuid4(),
                    target_user_id=None,
                    target_org_id=org_id,
                    reason="compliance",
                    delete_after=now,
                    processed_at=None,
                    created_at=now,
                    updated_at=now,
                )
            ]

    monkeypatch.setattr(admin_module, "PrivacyService", _FakePrivacyService)
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)
    res = client.get(f"/api/v1/admin/deletion-requests?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(request_id)
    assert body["items"][0]["scope"] == "ORG"


def test_admin_dead_letter_list_endpoint(monkeypatch, admin_module):
    fake_dlq = FakeDeadLetterRepo(SimpleNamespace(org_id=uuid.uuid4()))
    monkeypatch.setattr(admin_module, "DeadLetterRepo", lambda _db: fake_dlq)
    org_id = uuid.uuid4()
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    res = client.get(f"/api/v1/admin/dead-letter?org_id={org_id}&status=OPEN")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["counts_by_status"]["OPEN"] == 1
    assert body["items"][0]["source_type"] == "OUTBOX"


def test_admin_dead_letter_replay_endpoint(monkeypatch, admin_module):
    fake_outbox = FakeOutboxRepo(None)
    fake_outbox.args = {"org_id": uuid.uuid4()}

    class _ReplayDeadLetterRepo(FakeDeadLetterRepo):
        async def by_id(self, dead_letter_id):
            now = datetime.now(timezone.utc)
            return SimpleNamespace(
                id=dead_letter_id,
                org_id=fake_outbox.args["org_id"],
                source_type="OUTBOX",
                source_id=uuid.uuid4(),
                source_task_id=None,
                source_name="email.send",
                status="OPEN",
                attempts=5,
                last_error="smtp timeout",
                payload={},
                metadata_json={},
                first_failed_at=now,
                last_failed_at=now,
                replayed_at=None,
                created_at=now,
                updated_at=now,
            )

    fake_dlq = _ReplayDeadLetterRepo(SimpleNamespace(org_id=fake_outbox.args["org_id"]))
    monkeypatch.setattr(admin_module, "DeadLetterRepo", lambda _db: fake_dlq)
    monkeypatch.setattr(admin_module, "OutboxRepo", lambda _db: fake_outbox)
    org_id = fake_outbox.args["org_id"]
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    event_id = uuid.uuid4()
    res = client.post(f"/api/v1/admin/dead-letter/{event_id}/replay?org_id={org_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "REPLAYED"


def test_admin_dead_letter_dismiss_endpoint(monkeypatch, admin_module):
    org_id = uuid.uuid4()
    fake_dlq = FakeDeadLetterRepo(SimpleNamespace(org_id=org_id))
    monkeypatch.setattr(admin_module, "DeadLetterRepo", lambda _db: fake_dlq)
    app = _app_with_overrides(monkeypatch, admin_module, "OWNER", org_id)
    client = TestClient(app)

    event_id = uuid.uuid4()
    res = client.post(
        f"/api/v1/admin/dead-letter/{event_id}/dismiss?org_id={org_id}&reason=resolved"
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "DISMISSED"
