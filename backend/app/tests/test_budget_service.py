from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.services.budget_service import BudgetService


@dataclass
class _BudgetRow:
    id: object
    org_id: object
    created_by_user_id: object
    category: str
    period_month: date
    budget_type: str
    planned_amount: Decimal
    notes: str | None
    version: int
    is_current: bool
    created_at: datetime
    updated_at: datetime


class _FakeBudgetRepo:
    def __init__(self):
        self.rows: list[_BudgetRow] = []

    async def list_budgets(self, org_id, period_month=None, budget_type=None, include_history=False):
        rows = [row for row in self.rows if row.org_id == org_id]
        if period_month:
            rows = [row for row in rows if row.period_month == period_month]
        if budget_type:
            rows = [row for row in rows if row.budget_type == budget_type]
        if not include_history:
            rows = [row for row in rows if row.is_current]
        return rows

    async def max_version(self, *, org_id, category, period_month, budget_type):
        versions = [
            row.version
            for row in self.rows
            if row.org_id == org_id
            and row.category == category
            and row.period_month == period_month
            and row.budget_type == budget_type
        ]
        return max(versions) if versions else 0

    async def clear_current(self, *, org_id, category, period_month, budget_type):
        count = 0
        for row in self.rows:
            if (
                row.org_id == org_id
                and row.category == category
                and row.period_month == period_month
                and row.budget_type == budget_type
                and row.is_current
            ):
                row.is_current = False
                count += 1
        return count

    async def save(self, budget):
        row = _BudgetRow(
            id=getattr(budget, "id", uuid4()),
            org_id=budget.org_id,
            created_by_user_id=budget.created_by_user_id,
            category=budget.category,
            period_month=budget.period_month,
            budget_type=budget.budget_type,
            planned_amount=Decimal(str(budget.planned_amount)),
            notes=budget.notes,
            version=budget.version,
            is_current=budget.is_current,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.rows.append(row)
        return row

    async def get_budget(self, budget_id, org_id):
        for row in self.rows:
            if row.id == budget_id and row.org_id == org_id:
                return row
        return None

    async def monthly_actuals_by_category(
        self,
        *,
        org_id,
        period_start,
        period_end_exclusive,
        budget_type=None,
        location_id=None,
    ):
        _ = (org_id, period_start, period_end_exclusive, budget_type, location_id)
        if budget_type == "REVENUE":
            return {"Sales": Decimal("1200.00")}
        return {"Ops": Decimal("1100.00"), "Misc": Decimal("150.00")}


class _FakeBudgetRepoTyped(_FakeBudgetRepo):
    async def monthly_actuals_by_category(
        self,
        *,
        org_id,
        period_start,
        period_end_exclusive,
        budget_type=None,
        location_id=None,
    ):
        _ = (org_id, period_start, period_end_exclusive, location_id)
        if budget_type == "REVENUE":
            return {"Sales": Decimal("1200.00")}
        if budget_type == "EXPENSE":
            return {"Sales": Decimal("400.00"), "Ops": Decimal("1100.00")}
        return {}


@pytest.mark.asyncio
async def test_create_budget_versions_replace_current():
    repo = _FakeBudgetRepo()
    svc = BudgetService(repo)  # type: ignore[arg-type]
    org_id = uuid4()
    user_id = uuid4()
    period = date(2026, 4, 19)

    first = await svc.create_budget(
        org_id=org_id,
        actor_user_id=user_id,
        category="Ops",
        period_month=period,
        planned_amount=Decimal("1000.00"),
        budget_type="EXPENSE",
        notes="v1",
    )
    second = await svc.create_budget(
        org_id=org_id,
        actor_user_id=user_id,
        category="Ops",
        period_month=period,
        planned_amount=Decimal("1250.00"),
        budget_type="EXPENSE",
        notes="v2",
    )

    assert first.version == 1
    assert second.version == 2
    current_rows = await repo.list_budgets(org_id=org_id)
    assert len(current_rows) == 1
    assert current_rows[0].version == 2
    assert current_rows[0].planned_amount == Decimal("1250.00")


@pytest.mark.asyncio
async def test_budget_variance_includes_unbudgeted_actual_category():
    repo = _FakeBudgetRepo()
    svc = BudgetService(repo)  # type: ignore[arg-type]
    org_id = uuid4()
    user_id = uuid4()
    await svc.create_budget(
        org_id=org_id,
        actor_user_id=user_id,
        category="Ops",
        period_month=date(2026, 3, 1),
        planned_amount=Decimal("1000.00"),
        budget_type="EXPENSE",
    )

    out = await svc.budget_variance(org_id=org_id, period_month=date(2026, 3, 15), budget_type="EXPENSE")

    assert out["budget_type"] == "EXPENSE"
    assert out["totals"]["planned_amount"] == Decimal("1000.00")
    assert out["totals"]["actual_amount"] == Decimal("1250.00")
    assert out["totals"]["variance_amount"] == Decimal("250.00")
    categories = {line.category for line in out["lines"]}
    assert "Ops" in categories
    assert "Misc" in categories


@pytest.mark.asyncio
async def test_budget_variance_all_mode_separates_actuals_by_type():
    repo = _FakeBudgetRepoTyped()
    svc = BudgetService(repo)  # type: ignore[arg-type]
    org_id = uuid4()
    user_id = uuid4()
    period = date(2026, 3, 1)
    await svc.create_budget(
        org_id=org_id,
        actor_user_id=user_id,
        category="Sales",
        period_month=period,
        planned_amount=Decimal("300.00"),
        budget_type="EXPENSE",
    )
    await svc.create_budget(
        org_id=org_id,
        actor_user_id=user_id,
        category="Sales",
        period_month=period,
        planned_amount=Decimal("1000.00"),
        budget_type="REVENUE",
    )

    out = await svc.budget_variance(org_id=org_id, period_month=period, budget_type=None)
    by_type = {(line.category, line.budget_type): line for line in out["lines"]}

    assert by_type[("Sales", "EXPENSE")].actual_amount == Decimal("400.00")
    assert by_type[("Sales", "REVENUE")].actual_amount == Decimal("1200.00")
