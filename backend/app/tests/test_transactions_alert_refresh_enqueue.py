from datetime import date, datetime, timezone
from decimal import Decimal
from importlib import reload
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def transactions_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.transactions as transactions

    return reload(transactions)


class _FakeDb:
    async def commit(self):
        return None


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


class _FakeImportRepo:
    def __init__(self, _db):
        pass


class _FakePlanRepo:
    def __init__(self, _db):
        pass


class _FakeUsageService:
    def __init__(self, _repo):
        pass


class _FakeIdempotencyService:
    replay = None

    def __init__(self, _repo):
        pass

    async def get_replay(self, **_kwargs):
        return _FakeIdempotencyService.replay

    async def store_response(self, **_kwargs):
        return None


class _FakeTxService:
    def __init__(self):
        self.actions: list[tuple[str, str]] = []
        self.bulk_updated = 2

    @staticmethod
    def _tx(org_id):
        return SimpleNamespace(
            id=uuid4(),
            org_id=org_id,
            date=date(2026, 3, 10),
            amount=Decimal("100.00"),
            type="EXPENSE",
            category="Ops",
            vendor=None,
            notes=None,
            created_by=uuid4(),
            created_at=datetime.now(timezone.utc),
        )

    async def create(self, _user_id, payload):
        self.actions.append(("create", str(payload.org_id)))
        return self._tx(payload.org_id)

    async def update(self, _user_id, org_id, _tx_id, _payload):
        self.actions.append(("update", str(org_id)))
        return self._tx(org_id)

    async def delete(self, _user_id, org_id, _tx_id):
        self.actions.append(("delete", str(org_id)))
        return None

    async def bulk_remap_category(self, *, user_id, org_id, from_category, to_category, from_date=None, to_date=None):
        _ = (user_id, from_category, to_category, from_date, to_date)
        self.actions.append(("bulk_remap", str(org_id)))
        return self.bulk_updated


_ALERT_REFRESH_CALLS: list[dict] = []
_NOTIFICATION_CALLS: list[dict] = []


class _FakeAlertRefreshService:
    def __init__(self, _job_repo):
        pass

    async def enqueue_recalc(self, **kwargs):
        _ALERT_REFRESH_CALLS.append(kwargs)
        return SimpleNamespace(task_id="recalc-alerts-job", status="PENDING", enqueued=True)


class _FakeNotificationService:
    def __init__(self, _repo):
        pass

    async def create_org_notification(self, **kwargs):
        _NOTIFICATION_CALLS.append(kwargs)
        return None


def _app(monkeypatch, module, role: str = "OWNER"):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/transactions")
    user = SimpleNamespace(id=uuid4(), email="owner@example.com")

    async def fake_user():
        return user

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    from app.api import deps as shared_deps

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_current_user] = fake_user
    app.dependency_overrides[shared_deps.get_db] = fake_db
    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    app.dependency_overrides[module.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(module, "ImportRepo", _FakeImportRepo)
    monkeypatch.setattr(module, "PlanRepo", _FakePlanRepo)
    monkeypatch.setattr(module, "UsageService", _FakeUsageService)
    monkeypatch.setattr(module, "IdempotencyService", _FakeIdempotencyService)
    monkeypatch.setattr(module, "IdempotencyRepo", lambda _db: object())
    monkeypatch.setattr(module, "AlertRefreshService", _FakeAlertRefreshService)
    monkeypatch.setattr(module, "JobRepo", lambda _db: object())
    monkeypatch.setattr(module, "NotificationRepo", lambda _db: object())
    monkeypatch.setattr(module, "NotificationService", _FakeNotificationService)

    async def _noop_cache_delete(_prefix):
        return None

    monkeypatch.setattr(module, "cache_delete_prefix", _noop_cache_delete)
    return app, user


def test_transaction_mutations_enqueue_alert_recalc(monkeypatch, transactions_module):
    _ALERT_REFRESH_CALLS.clear()
    _NOTIFICATION_CALLS.clear()
    _FakeIdempotencyService.replay = None
    fake_tx = _FakeTxService()
    monkeypatch.setattr(transactions_module, "TransactionService", lambda *args, **kwargs: fake_tx)
    app, _user = _app(monkeypatch, transactions_module, role="OWNER")
    client = TestClient(app)
    org_id = str(uuid4())
    tx_id = str(uuid4())

    create_res = client.post(
        "/api/v1/transactions",
        json={
            "org_id": org_id,
            "date": "2026-03-10",
            "amount": "100.00",
            "type": "EXPENSE",
            "category": "Ops",
        },
    )
    assert create_res.status_code == 200, create_res.text
    assert create_res.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"
    assert create_res.headers["X-Alert-Recalc-Queued"] == "true"

    update_res = client.put(
        f"/api/v1/transactions/{tx_id}?org_id={org_id}",
        json={"category": "Operations"},
    )
    assert update_res.status_code == 200, update_res.text
    assert update_res.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"

    delete_res = client.delete(f"/api/v1/transactions/{tx_id}?org_id={org_id}")
    assert delete_res.status_code == 200, delete_res.text
    assert delete_res.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"

    remap_res = client.post(
        f"/api/v1/transactions/bulk/remap-category?org_id={org_id}",
        json={"org_id": org_id, "from_category": "Ops", "to_category": "Operations"},
    )
    assert remap_res.status_code == 200, remap_res.text
    assert remap_res.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"

    reasons = [call.get("reason") for call in _ALERT_REFRESH_CALLS]
    assert reasons == [
        "transaction.create",
        "transaction.update",
        "transaction.delete",
        "transaction.bulk_remap_category",
    ]
    assert len(_NOTIFICATION_CALLS) == 4
    assert _NOTIFICATION_CALLS[0]["metadata_json"]["source"] == "transaction.create"
    assert _NOTIFICATION_CALLS[-1]["metadata_json"]["source"] == "transaction.bulk_remap_category"
    assert fake_tx.actions == [
        ("create", org_id),
        ("update", org_id),
        ("delete", org_id),
        ("bulk_remap", org_id),
    ]


def test_transaction_create_idempotent_replay_skips_enqueue(monkeypatch, transactions_module):
    _ALERT_REFRESH_CALLS.clear()
    _NOTIFICATION_CALLS.clear()
    _FakeIdempotencyService.replay = SimpleNamespace(status_code=200, response_json={"transaction": {"id": "replayed"}})
    fake_tx = _FakeTxService()
    monkeypatch.setattr(transactions_module, "TransactionService", lambda *args, **kwargs: fake_tx)
    app, _user = _app(monkeypatch, transactions_module, role="OWNER")
    client = TestClient(app)

    res = client.post(
        "/api/v1/transactions",
        json={
            "org_id": str(uuid4()),
            "date": "2026-03-10",
            "amount": "99.00",
            "type": "EXPENSE",
            "category": "Ops",
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["transaction"]["id"] == "replayed"
    assert _ALERT_REFRESH_CALLS == []
    assert _NOTIFICATION_CALLS == []
    assert fake_tx.actions == []
    _FakeIdempotencyService.replay = None


def test_bulk_remap_zero_updates_does_not_enqueue(monkeypatch, transactions_module):
    _ALERT_REFRESH_CALLS.clear()
    _NOTIFICATION_CALLS.clear()
    _FakeIdempotencyService.replay = None
    fake_tx = _FakeTxService()
    fake_tx.bulk_updated = 0
    monkeypatch.setattr(transactions_module, "TransactionService", lambda *args, **kwargs: fake_tx)
    app, _user = _app(monkeypatch, transactions_module, role="OWNER")
    client = TestClient(app)

    org_id = str(uuid4())
    res = client.post(
        f"/api/v1/transactions/bulk/remap-category?org_id={org_id}",
        json={"org_id": org_id, "from_category": "Ops", "to_category": "Operations"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["updated_count"] == 0
    assert _ALERT_REFRESH_CALLS == []
    assert _NOTIFICATION_CALLS == []
