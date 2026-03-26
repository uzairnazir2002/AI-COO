import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.budget import Budget
from app.domain.models.transaction import Transaction


class BudgetRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_budgets(
        self,
        org_id: uuid.UUID,
        period_month: date | None = None,
        budget_type: str | None = None,
        include_history: bool = False,
    ) -> list[Budget]:
        q = select(Budget).where(Budget.org_id == org_id)
        if period_month:
            q = q.where(Budget.period_month == period_month)
        if budget_type:
            q = q.where(Budget.budget_type == budget_type)
        if not include_history:
            q = q.where(Budget.is_current.is_(True))
        q = q.order_by(Budget.period_month.desc(), Budget.budget_type.asc(), Budget.category.asc(), Budget.version.desc())
        res = await self.db.execute(q)
        return list(res.scalars().all())

    async def get_budget(self, budget_id: uuid.UUID, org_id: uuid.UUID) -> Budget | None:
        res = await self.db.execute(select(Budget).where(Budget.id == budget_id, Budget.org_id == org_id))
        return res.scalar_one_or_none()

    async def max_version(
        self,
        *,
        org_id: uuid.UUID,
        category: str,
        period_month: date,
        budget_type: str,
    ) -> int:
        res = await self.db.scalar(
            select(func.max(Budget.version)).where(
                Budget.org_id == org_id,
                Budget.category == category,
                Budget.period_month == period_month,
                Budget.budget_type == budget_type,
            )
        )
        return int(res or 0)

    async def clear_current(
        self,
        *,
        org_id: uuid.UUID,
        category: str,
        period_month: date,
        budget_type: str,
    ) -> int:
        result = await self.db.execute(
            update(Budget)
            .where(
                Budget.org_id == org_id,
                Budget.category == category,
                Budget.period_month == period_month,
                Budget.budget_type == budget_type,
                Budget.is_current.is_(True),
            )
            .values(is_current=False)
        )
        return int(result.rowcount or 0)

    async def save(self, budget: Budget) -> Budget:
        self.db.add(budget)
        await self.db.flush()
        return budget

    async def monthly_actuals_by_category(
        self,
        *,
        org_id: uuid.UUID,
        period_start: date,
        period_end_exclusive: date,
        budget_type: str | None = None,
        location_id: uuid.UUID | None = None,
    ) -> dict[str, Decimal]:
        q = (
            select(Transaction.category, func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                Transaction.org_id == org_id,
                Transaction.date >= period_start,
                Transaction.date < period_end_exclusive,
            )
            .group_by(Transaction.category)
        )
        if budget_type:
            q = q.where(Transaction.type == budget_type)
        if location_id is not None:
            q = q.where(Transaction.location_id == location_id)
        res = await self.db.execute(q)
        return {str(category): Decimal(total or 0) for category, total in res.all()}
