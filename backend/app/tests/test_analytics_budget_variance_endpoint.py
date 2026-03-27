import uuid
from datetime import date
from importlib import reload
from types import SimpleNamespace
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def analytics_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.analytics as analytics

    return reload(analytics)


class _FakeDb:
    async def commit(self):
        return None


class _FakeBudgetLine:
    def __init__(self, category: str, budget_type: str, planned: str, actual: str, variance: str, variance_pct: str | None):
        self.category = category
        self.budget_type = budget_type
        self.planned_amount = Decimal(planned)
        self.actual_amount = Decimal(actual)
        self.variance_amount = Decimal(variance)
        self.variance_pct = Decimal(variance_pct) if variance_pct is not None else None


class _FakeBudgetService:
    def __init__(self, *_args, **_kwargs):
        pass

    async def budget_variance(self, *, org_id, period_month, budget_type, location_id=None):
        _ = (budget_type, location_id)
        return {
            "org_id": org_id,
            "period_month": period_month.replace(day=1),
            "budget_type": "EXPENSE",
            "totals": {
                "planned_amount": Decimal("1000.00"),
                "actual_amount": Decimal("1250.00"),
                "variance_amount": Decimal("250.00"),
            },
            "lines": [
                _FakeBudgetLine("Ops", "EXPENSE", "1000.00", "1100.00", "100.00", "10.00"),
                _FakeBudgetLine("Misc", "EXPENSE", "0.00", "150.00", "150.00", None),
            ],
        }


def _app(monkeypatch, module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/analytics")

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "BudgetService", _FakeBudgetService)
    monkeypatch.setattr(module, "BudgetRepo", lambda _db: object())
    return app


def test_budget_variance_endpoint(monkeypatch, analytics_module):
    app = _app(monkeypatch, analytics_module)
    client = TestClient(app)
    org_id = uuid.uuid4()

    res = client.get(f"/api/v1/analytics/budget-variance?org_id={org_id}&period={date(2026, 3, 12)}&budget_type=expense")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["period_month"] == "2026-03-01"
    assert body["budget_type"] == "EXPENSE"
    assert body["totals"]["variance_amount"] == "250.00"
    assert len(body["lines"]) == 2
