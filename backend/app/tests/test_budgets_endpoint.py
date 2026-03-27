import uuid
from datetime import datetime, timezone
from importlib import reload
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def budgets_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.budgets as budgets

    return reload(budgets)


class _FakeDb:
    async def commit(self):
        return None


class _FakeBudgetService:
    def __init__(self, *_args, **_kwargs):
        self.rows = _ROWS

    async def list_budgets(
        self, *, org_id, period_month=None, budget_type=None, include_history=False
    ):
        out = [row for row in self.rows if row.org_id == org_id]
        if period_month:
            out = [row for row in out if row.period_month == period_month]
        if budget_type:
            out = [row for row in out if row.budget_type == budget_type]
        if not include_history:
            out = [row for row in out if row.is_current]
        return out

    async def create_budget(
        self,
        *,
        org_id,
        actor_user_id,
        category,
        period_month,
        planned_amount,
        budget_type="EXPENSE",
        notes=None,
    ):
        _ = actor_user_id
        version = (
            max(
                (
                    row.version
                    for row in self.rows
                    if row.org_id == org_id
                    and row.category == category
                    and row.period_month == period_month.replace(day=1)
                    and row.budget_type == budget_type.upper()
                ),
                default=0,
            )
            + 1
        )
        for row in self.rows:
            if (
                row.org_id == org_id
                and row.category == category
                and row.period_month == period_month.replace(day=1)
                and row.budget_type == budget_type.upper()
                and row.is_current
            ):
                row.is_current = False
        row = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            category=category,
            period_month=period_month.replace(day=1),
            budget_type=budget_type.upper(),
            planned_amount=planned_amount,
            notes=notes,
            version=version,
            is_current=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.rows.append(row)
        return row

    async def update_budget_version(
        self, *, org_id, actor_user_id, budget_id, planned_amount, notes=None
    ):
        _ = actor_user_id
        row = next(
            (item for item in self.rows if item.id == budget_id and item.org_id == org_id),
            None,
        )
        if not row:
            raise ValueError("Budget not found")
        return await self.create_budget(
            org_id=org_id,
            actor_user_id=uuid.uuid4(),
            category=row.category,
            period_month=row.period_month,
            planned_amount=planned_amount,
            budget_type=row.budget_type,
            notes=notes,
        )


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *args, **kwargs):
        _ = (args, kwargs)


_ROWS: list[SimpleNamespace] = []
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


def _app(monkeypatch, module, role="OWNER"):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/budgets")
    user = SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_user():
        return user

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role=role)

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "BudgetService", _FakeBudgetService)
    monkeypatch.setattr(module, "BudgetRepo", lambda _db: object())
    monkeypatch.setattr(module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(module, "JobRepo", lambda _db: object())
    monkeypatch.setattr(module, "AlertRefreshService", _FakeAlertRefreshService)
    monkeypatch.setattr(module, "NotificationRepo", lambda _db: object())
    monkeypatch.setattr(module, "NotificationService", _FakeNotificationService)
    return app


def test_budget_create_list_update_flow(monkeypatch, budgets_module):
    _ROWS.clear()
    _ALERT_REFRESH_CALLS.clear()
    _NOTIFICATION_CALLS.clear()
    app = _app(monkeypatch, budgets_module)
    client = TestClient(app)
    org_id = str(uuid.uuid4())

    create = client.post(
        "/api/v1/budgets",
        json={
            "org_id": org_id,
            "category": "Ops",
            "period_month": "2026-03-01",
            "budget_type": "EXPENSE",
            "planned_amount": "1000.00",
            "notes": "baseline",
        },
    )
    assert create.status_code == 200, create.text
    assert create.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"
    assert create.headers["X-Alert-Recalc-Queued"] == "true"
    created = create.json()
    assert created["version"] == 1
    assert created["is_current"] is True

    listing = client.get(f"/api/v1/budgets?org_id={org_id}&period=2026-03-01")
    assert listing.status_code == 200, listing.text
    assert len(listing.json()) == 1

    update = client.put(
        f"/api/v1/budgets/{created['id']}",
        json={"org_id": org_id, "planned_amount": "1200.00", "notes": "uplift"},
    )
    assert update.status_code == 200, update.text
    assert update.headers["X-Alert-Recalc-Task-Id"] == "recalc-alerts-job"
    updated = update.json()
    assert updated["version"] == 2
    assert updated["planned_amount"] == "1200.00"

    current = client.get(f"/api/v1/budgets?org_id={org_id}&period=2026-03-01")
    assert current.status_code == 200
    current_rows = current.json()
    assert len(current_rows) == 1
    assert current_rows[0]["version"] == 2

    history = client.get(f"/api/v1/budgets?org_id={org_id}&period=2026-03-01&include_history=true")
    assert history.status_code == 200
    assert len(history.json()) == 2

    assert len(_ALERT_REFRESH_CALLS) == 2
    assert _ALERT_REFRESH_CALLS[0]["reason"] == "budget.create"
    assert _ALERT_REFRESH_CALLS[1]["reason"] == "budget.update"
    assert len(_NOTIFICATION_CALLS) == 2
    assert _NOTIFICATION_CALLS[0]["title"] == "Alert refresh queued"
    assert _NOTIFICATION_CALLS[0]["metadata_json"]["event"] == "alert.recalc.enqueue"
    assert _NOTIFICATION_CALLS[1]["metadata_json"]["source"] == "budget.update"


def test_budget_mutations_forbidden_for_viewer(monkeypatch, budgets_module):
    _ROWS.clear()
    _ALERT_REFRESH_CALLS.clear()
    _NOTIFICATION_CALLS.clear()
    app = _app(monkeypatch, budgets_module, role="VIEWER")
    client = TestClient(app)
    org_id = str(uuid.uuid4())

    create = client.post(
        "/api/v1/budgets",
        json={
            "org_id": org_id,
            "category": "Ops",
            "period_month": "2026-03-01",
            "budget_type": "EXPENSE",
            "planned_amount": "1000.00",
        },
    )
    assert create.status_code == 403
    assert _ALERT_REFRESH_CALLS == []
    assert _NOTIFICATION_CALLS == []
