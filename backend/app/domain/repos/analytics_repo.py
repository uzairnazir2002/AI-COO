import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.alert import Alert
from app.domain.models.monthly_aggregate import MonthlyAggregate
from app.domain.models.organization_setting import OrganizationSetting
from app.domain.models.transaction import Transaction


class AnalyticsRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def month_totals(self, org_id: uuid.UUID, month: date) -> tuple[Decimal, Decimal]:
        q = await self.db.execute(
            select(MonthlyAggregate).where(MonthlyAggregate.org_id == org_id, MonthlyAggregate.year_month == month)
        )
        row = q.scalar_one_or_none()
        if row is None:
            return Decimal("0"), Decimal("0")
        return row.revenue_total, row.expense_total

    async def cash_balance(self, org_id: uuid.UUID) -> Decimal:
        start = await self.db.scalar(
            select(OrganizationSetting.starting_cash).where(OrganizationSetting.org_id == org_id)
        )
        rev = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id, Transaction.type == "REVENUE"
            )
        )
        exp = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id, Transaction.type == "EXPENSE"
            )
        )
        return Decimal(start or 0) + Decimal(rev or 0) - Decimal(exp or 0)

    async def monthly_lookback(self, org_id: uuid.UUID, months: int) -> list[MonthlyAggregate]:
        q = await self.db.execute(
            select(MonthlyAggregate)
            .where(MonthlyAggregate.org_id == org_id)
            .order_by(MonthlyAggregate.year_month.desc())
            .limit(months)
        )
        return list(q.scalars().all())

    async def alerts_open_count(self, org_id: uuid.UUID) -> int:
        c = await self.db.scalar(
            select(func.count()).select_from(Alert).where(Alert.org_id == org_id, Alert.status == "OPEN")
        )
        return int(c or 0)

    async def runway_threshold_days(self, org_id: uuid.UUID) -> int:
        threshold = await self.db.scalar(
            select(OrganizationSetting.runway_alert_threshold_days).where(OrganizationSetting.org_id == org_id)
        )
        return int(threshold or 60)
