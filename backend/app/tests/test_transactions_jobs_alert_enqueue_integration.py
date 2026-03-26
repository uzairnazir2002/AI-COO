from datetime import date, datetime, timezone
from decimal import Decimal
from importlib import reload
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps as shared_deps
import app.domain.services.alerts_refresh_service as alerts_refresh_module


class _SharedJobRepo:
    def __init__(self):
        self.rows: list[SimpleNamespace] = []

    async def by_dedupe_key(self, dedupe_key: str, org_id: UUID | None = None):
        for row in reversed(self.rows):
            if row.dedupe_key == dedupe_key and (org_id is None or row.org_id == org_id):
                return row
        return None

    async def upsert_pending(
        self,
        *,
        task_id: str,
        task_name: str,
        dedupe_key: str,
        payload: dict,
        org_id: UUID | None,
        request_id: str | None,
        correlation_id: str | None,
    ):
        now = datetime.now(timezone.utc)
        existing = None
        for row in self.rows:
            if row.task_id == task_id or row.dedupe_key == dedupe_key:
                existing = row
                break
        if existing is None:
            existing = SimpleNamespace(
                id=uuid4(),
                org_id=org_id,
                task_id=task_id,
                task_name=task_name,
                dedupe_key=dedupe_key,
                status="PENDING",
                progress=0,
                payload=payload,
                result=None,
                request_id=request_id,
                correlation_id=correlation_id,
                last_error=None,
                traceback_summary=None,
                retry_count=0,
                last_retry_at=None,
                created_at=now,
                updated_at=now,
            )
            self.rows.append(existing)
        else:
            existing.status = "PENDING"
            existing.progress = 0
            existing.payload = payload
            existing.request_id = request_id
            existing.correlation_id = correlation_id
            existing.updated_at = now
        return existing

    async def list_jobs(
        self,
        *,
        org_id: UUID,
        status: str | None,
        task_name: str | None,
        since,
        until,
        page: int,
        page_size: int,
    ):
        _ = (since, until)
        rows = [row for row in self.rows if row.org_id == org_id]
        if status:
            rows = [row for row in rows if row.status == status]
        if task_name:
            rows = [row for row in rows if row.task_name == task_name]
        rows = sorted(rows, key=lambda row: row.created_at, reverse=True)
        total = len(rows)
        start = (page - 1) * page_size
        return rows[start : start + page_size], total


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


class _FakeIdempotencyService:
    def __init__(self, _repo):
        pass

    async def get_replay(self, **_kwargs):
        return None

    async def store_response(self, **_kwargs):
        return None


class _FakeTxService:
    def __init__(self, *_args, **_kwargs):
        pass

    async def create(self, user_id, payload):
        return SimpleNamespace(
            id=uuid4(),
            org_id=payload.org_id,
            date=payload.date,
            amount=payload.amount,
            type=payload.type,
            category=payload.category,
            vendor=payload.vendor,
            notes=payload.notes,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
        )


class _FakeNotificationService:
    def __init__(self, _repo):
        pass

    async def create_org_notification(self, **_kwargs):
        return None


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.transactions as transactions
    import app.api.v1.jobs as jobs

    return reload(transactions), reload(jobs)


def test_transaction_create_enqueues_alert_job_visible_in_jobs_endpoint(monkeypatch, modules):
    transactions_module, jobs_module = modules
    shared_repo = _SharedJobRepo()
    org_id = uuid4()
    user_id = uuid4()

    class _FakeTask:
        def apply_async(self, *args, **kwargs):
            _ = (args, kwargs)
            return SimpleNamespace(id=f"task-{uuid4().hex[:10]}")

    monkeypatch.setattr(alerts_refresh_module, "recalc_alerts", _FakeTask())

    monkeypatch.setattr(transactions_module, "JobRepo", lambda _db: shared_repo)
    monkeypatch.setattr(jobs_module, "JobRepo", lambda _db: shared_repo)
    monkeypatch.setattr(transactions_module, "TransactionService", _FakeTxService)
    monkeypatch.setattr(transactions_module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(transactions_module, "IdempotencyService", _FakeIdempotencyService)
    monkeypatch.setattr(transactions_module, "IdempotencyRepo", lambda _db: object())
    monkeypatch.setattr(transactions_module, "TransactionRepo", lambda _db: object())
    monkeypatch.setattr(transactions_module, "ImportRepo", lambda _db: object())
    monkeypatch.setattr(transactions_module, "PlanRepo", lambda _db: object())
    monkeypatch.setattr(transactions_module, "UsageService", lambda _repo: object())
    monkeypatch.setattr(transactions_module, "NotificationRepo", lambda _db: object())
    monkeypatch.setattr(transactions_module, "NotificationService", _FakeNotificationService)

    async def _noop_cache_delete(_prefix):
        return None

    monkeypatch.setattr(transactions_module, "cache_delete_prefix", _noop_cache_delete)

    app = FastAPI()
    app.include_router(transactions_module.router, prefix="/api/v1/transactions")
    app.include_router(jobs_module.router, prefix="/api/v1/jobs")

    class _FakeDb:
        async def commit(self):
            return None

    async def fake_db():
        yield _FakeDb()

    async def fake_user():
        return SimpleNamespace(id=user_id, email="owner@example.com", is_active=True)

    async def fake_ctx(org_id, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    app.dependency_overrides[transactions_module.get_db] = fake_db
    app.dependency_overrides[transactions_module.get_current_user] = fake_user
    app.dependency_overrides[transactions_module.get_org_context] = fake_ctx
    app.dependency_overrides[jobs_module.get_db] = fake_db
    app.dependency_overrides[jobs_module.get_current_user] = fake_user
    app.dependency_overrides[jobs_module.get_org_context] = fake_ctx
    transactions_module.get_org_context = fake_ctx
    jobs_module.get_org_context = fake_ctx

    client = TestClient(app)
    create = client.post(
        "/api/v1/transactions",
        json={
            "org_id": str(org_id),
            "date": date(2026, 3, 12).isoformat(),
            "amount": str(Decimal("150.00")),
            "type": "EXPENSE",
            "category": "Ops",
        },
    )
    assert create.status_code == 200, create.text
    assert create.headers["X-Alert-Recalc-Task-Id"].startswith("task-")

    jobs = client.get(f"/api/v1/jobs?org_id={org_id}&status=PENDING&page=1&page_size=20")
    assert jobs.status_code == 200, jobs.text
    payload = jobs.json()
    assert payload["total"] >= 1
    row = payload["items"][0]
    assert row["org_id"] == str(org_id)
    assert row["task_name"] == "recalc_alerts"
    assert row["status"] == "PENDING"
    assert row["dedupe_key"] == f"alerts:{org_id}"
    assert row["payload"]["org_id"] == str(org_id)
