from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeJobRepo:
    def __init__(self, _db):
        self.pending_calls = []
        self.succeeded_calls = []
        self.existing_job = None

    async def by_dedupe_key(self, _dedupe_key, _org_id=None):
        return self.existing_job

    async def upsert_pending(self, **kwargs):
        self.pending_calls.append(kwargs)
        return SimpleNamespace(task_id=kwargs["task_id"], status="PENDING")

    async def mark_succeeded(self, task_id, result):
        self.succeeded_calls.append({"task_id": task_id, "result": result})


class _FakeReportRepo:
    def __init__(self, _db):
        self.existing_report = None

    async def get_by_week(self, _org_id, _week_start, *, location_id=None):
        return self.existing_report


class _FakeUsageService:
    consumed = 0

    def __init__(self, _plan_repo):
        pass

    async def consume(self, _org_id, _metric, delta=1):
        type(self).consumed += delta


class _FakeAuditRepo:
    def __init__(self, _db):
        self.actions = []

    async def log(self, _user_id, _org_id, action, _entity_type, _entity_id, _metadata):
        self.actions.append(action)


class _FakeIdempotencyService:
    replay = None

    def __init__(self, _repo):
        pass

    async def get_replay(self, **_kwargs):
        return type(self).replay

    async def store_response(self, **_kwargs):
        return None


@pytest.fixture
def reports_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.reports as reports

    return reload(reports)


def _app_with_overrides(reports_module, monkeypatch, org_id: uuid.UUID, user_id: uuid.UUID):
    app = FastAPI()
    app.include_router(reports_module.router, prefix="/api/v1/reports")

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

    app.dependency_overrides[reports_module.get_current_user] = fake_user
    app.dependency_overrides[reports_module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(reports_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(reports_module, "IdempotencyService", _FakeIdempotencyService)
    monkeypatch.setattr(reports_module, "IdempotencyRepo", lambda _db: object())
    return app


def test_generate_report_enqueues_async_job(monkeypatch, reports_module):
    _FakeIdempotencyService.replay = None
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_job_repo = _FakeJobRepo(object())
    fake_report_repo = _FakeReportRepo(object())
    fake_audit_repo = _FakeAuditRepo(object())

    monkeypatch.setattr(reports_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(reports_module, "ReportRepo", lambda _db: fake_report_repo)
    monkeypatch.setattr(reports_module, "AuditRepo", lambda _db: fake_audit_repo)
    monkeypatch.setattr(reports_module, "PlanRepo", lambda _db: object())
    monkeypatch.setattr(reports_module, "UsageService", _FakeUsageService)
    monkeypatch.setattr(
        reports_module,
        "generate_weekly_report",
        SimpleNamespace(apply_async=lambda args: SimpleNamespace(id="celery-task-1")),
    )

    app = _app_with_overrides(reports_module, monkeypatch, org_id, user_id)
    client = TestClient(app)

    res = client.post(f"/api/v1/reports/generate?org_id={org_id}&week_start=2026-03-02")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["job_id"] == "celery-task-1"
    assert body["status"] == "PENDING"
    assert body["report_id"] is None
    assert len(fake_job_repo.pending_calls) == 1


def test_generate_report_returns_active_job_when_already_running(monkeypatch, reports_module):
    _FakeIdempotencyService.replay = None
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_job_repo = _FakeJobRepo(object())
    fake_job_repo.existing_job = SimpleNamespace(
        task_id="task-running", status="RUNNING", result=None
    )

    monkeypatch.setattr(reports_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(reports_module, "ReportRepo", lambda _db: _FakeReportRepo(object()))
    monkeypatch.setattr(reports_module, "AuditRepo", lambda _db: _FakeAuditRepo(object()))
    monkeypatch.setattr(
        reports_module,
        "generate_weekly_report",
        SimpleNamespace(
            apply_async=lambda args: (_ for _ in ()).throw(
                AssertionError("apply_async should not be called")
            )
        ),
    )

    app = _app_with_overrides(reports_module, monkeypatch, org_id, user_id)
    client = TestClient(app)

    res = client.post(f"/api/v1/reports/generate?org_id={org_id}&week_start=2026-03-02")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["job_id"] == "task-running"
    assert body["status"] == "RUNNING"


def test_generate_report_reuses_existing_report(monkeypatch, reports_module):
    _FakeIdempotencyService.replay = None
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()

    fake_job_repo = _FakeJobRepo(object())
    fake_report_repo = _FakeReportRepo(object())
    fake_report_repo.existing_report = SimpleNamespace(id=report_id)
    fake_audit_repo = _FakeAuditRepo(object())

    monkeypatch.setattr(reports_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(reports_module, "ReportRepo", lambda _db: fake_report_repo)
    monkeypatch.setattr(reports_module, "AuditRepo", lambda _db: fake_audit_repo)
    monkeypatch.setattr(reports_module, "PlanRepo", lambda _db: object())
    monkeypatch.setattr(reports_module, "UsageService", _FakeUsageService)

    app = _app_with_overrides(reports_module, monkeypatch, org_id, user_id)
    client = TestClient(app)

    res = client.post(f"/api/v1/reports/generate?org_id={org_id}&week_start=2026-03-02")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "SUCCEEDED"
    assert body["report_id"] == str(report_id)
    assert body["job_id"] == f"reused-{report_id}"
    assert len(fake_job_repo.succeeded_calls) == 0
    assert len(fake_audit_repo.actions) == 0


def test_generate_report_replays_from_idempotency_store(monkeypatch, reports_module):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()
    _FakeIdempotencyService.replay = SimpleNamespace(
        status_code=200,
        response_json={
            "report_id": str(report_id),
            "job_id": f"reused-{report_id}",
            "status": "SUCCEEDED",
        },
    )
    monkeypatch.setattr(
        reports_module,
        "generate_weekly_report",
        SimpleNamespace(
            apply_async=lambda args: (_ for _ in ()).throw(
                AssertionError("apply_async should not be called on replay")
            )
        ),
    )
    app = _app_with_overrides(reports_module, monkeypatch, org_id, user_id)
    client = TestClient(app)
    res = client.post(
        f"/api/v1/reports/generate?org_id={org_id}&week_start=2026-03-02",
        headers={"Idempotency-Key": "idem-rpt-1"},
    )
    assert res.status_code == 200
    assert res.json()["job_id"] == f"reused-{report_id}"


def test_generate_report_location_scope_changes_dedupe_key(monkeypatch, reports_module):
    _FakeIdempotencyService.replay = None
    org_id = uuid.uuid4()
    location_id = uuid.uuid4()
    user_id = uuid.uuid4()
    fake_job_repo = _FakeJobRepo(object())
    fake_report_repo = _FakeReportRepo(object())
    fake_audit_repo = _FakeAuditRepo(object())

    monkeypatch.setattr(reports_module, "JobRepo", lambda _db: fake_job_repo)
    monkeypatch.setattr(reports_module, "ReportRepo", lambda _db: fake_report_repo)
    monkeypatch.setattr(reports_module, "AuditRepo", lambda _db: fake_audit_repo)
    monkeypatch.setattr(reports_module, "PlanRepo", lambda _db: object())
    monkeypatch.setattr(reports_module, "UsageService", _FakeUsageService)

    class _FakeLocationService:
        def __init__(self, _repo):
            pass

        async def ensure_org_location(self, **_kwargs):
            return None

    monkeypatch.setattr(
        reports_module,
        "LocationService",
        _FakeLocationService,
    )
    monkeypatch.setattr(reports_module, "LocationRepo", lambda _db: object())
    monkeypatch.setattr(
        reports_module,
        "generate_weekly_report",
        SimpleNamespace(apply_async=lambda args: SimpleNamespace(id="celery-task-loc-1")),
    )

    app = _app_with_overrides(reports_module, monkeypatch, org_id, user_id)
    client = TestClient(app)

    res = client.post(
        f"/api/v1/reports/generate?org_id={org_id}&location_id={location_id}&week_start=2026-03-02"
    )
    assert res.status_code == 200, res.text
    assert res.json()["job_id"] == "celery-task-loc-1"
    assert len(fake_job_repo.pending_calls) == 1
    pending = fake_job_repo.pending_calls[0]
    assert pending["dedupe_key"] == f"report:{org_id}:{location_id}:2026-03-02"
    assert pending["payload"]["location_id"] == str(location_id)
