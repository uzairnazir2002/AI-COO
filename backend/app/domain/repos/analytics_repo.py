import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.alert import Alert
from app.domain.models.location import Location
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

    async def summary_snapshot(
        self,
        org_id: uuid.UUID,
        month: date,
        *,
        location_id: uuid.UUID | None = None,
    ) -> dict[str, Decimal | int]:
        if location_id is not None:
            return await self.summary_snapshot_for_location(org_id=org_id, month=month, location_id=location_id)
        row = await self.db.execute(
            select(
                func.coalesce(
                    select(OrganizationSetting.starting_cash).where(OrganizationSetting.org_id == org_id).scalar_subquery(),
                    0,
                ).label("starting_cash"),
                func.coalesce(
                    select(func.sum(MonthlyAggregate.revenue_total))
                    .where(MonthlyAggregate.org_id == org_id)
                    .scalar_subquery(),
                    0,
                ).label("revenue_total"),
                func.coalesce(
                    select(func.sum(MonthlyAggregate.expense_total))
                    .where(MonthlyAggregate.org_id == org_id)
                    .scalar_subquery(),
                    0,
                ).label("expense_total"),
                func.coalesce(
                    select(MonthlyAggregate.revenue_total)
                    .where(MonthlyAggregate.org_id == org_id, MonthlyAggregate.year_month == month)
                    .scalar_subquery(),
                    0,
                ).label("revenue_mtd"),
                func.coalesce(
                    select(MonthlyAggregate.expense_total)
                    .where(MonthlyAggregate.org_id == org_id, MonthlyAggregate.year_month == month)
                    .scalar_subquery(),
                    0,
                ).label("expense_mtd"),
                func.coalesce(
                    select(func.count()).select_from(Alert).where(Alert.org_id == org_id, Alert.status == "OPEN").scalar_subquery(),
                    0,
                ).label("alerts_open"),
            )
        )
        data = row.mappings().first() or {}
        return {
            "starting_cash": Decimal(data.get("starting_cash") or 0),
            "revenue_total": Decimal(data.get("revenue_total") or 0),
            "expense_total": Decimal(data.get("expense_total") or 0),
            "revenue_mtd": Decimal(data.get("revenue_mtd") or 0),
            "expense_mtd": Decimal(data.get("expense_mtd") or 0),
            "alerts_open": int(data.get("alerts_open") or 0),
        }

    async def summary_snapshot_for_location(
        self,
        *,
        org_id: uuid.UUID,
        month: date,
        location_id: uuid.UUID,
    ) -> dict[str, Decimal | int]:
        month_start = date(month.year, month.month, 1)
        if month_start.month == 12:
            month_end_exclusive = date(month_start.year + 1, 1, 1)
        else:
            month_end_exclusive = date(month_start.year, month_start.month + 1, 1)

        revenue_total = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.location_id == location_id,
                Transaction.type == "REVENUE",
            )
        )
        expense_total = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.location_id == location_id,
                Transaction.type == "EXPENSE",
            )
        )
        revenue_mtd = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.location_id == location_id,
                Transaction.type == "REVENUE",
                Transaction.date >= month_start,
                Transaction.date < month_end_exclusive,
            )
        )
        expense_mtd = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.location_id == location_id,
                Transaction.type == "EXPENSE",
                Transaction.date >= month_start,
                Transaction.date < month_end_exclusive,
            )
        )
        alerts_open = await self.db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.org_id == org_id,
                Alert.location_id == location_id,
                Alert.status == "OPEN",
            )
        )
        return {
            "starting_cash": Decimal("0"),
            "revenue_total": Decimal(revenue_total or 0),
            "expense_total": Decimal(expense_total or 0),
            "revenue_mtd": Decimal(revenue_mtd or 0),
            "expense_mtd": Decimal(expense_mtd or 0),
            "alerts_open": int(alerts_open or 0),
        }

    async def cash_balance(self, org_id: uuid.UUID, *, location_id: uuid.UUID | None = None) -> Decimal:
        if location_id is not None:
            rev = await self.db.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.org_id == org_id,
                    Transaction.location_id == location_id,
                    Transaction.type == "REVENUE",
                )
            )
            exp = await self.db.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                    Transaction.org_id == org_id,
                    Transaction.location_id == location_id,
                    Transaction.type == "EXPENSE",
                )
            )
            return Decimal(rev or 0) - Decimal(exp or 0)
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

    async def monthly_lookback(
        self,
        org_id: uuid.UUID,
        months: int,
        *,
        location_id: uuid.UUID | None = None,
    ) -> list[MonthlyAggregate]:
        if location_id is None:
            q = await self.db.execute(
                select(MonthlyAggregate)
                .where(MonthlyAggregate.org_id == org_id)
                .order_by(MonthlyAggregate.year_month.desc())
                .limit(months)
            )
            return list(q.scalars().all())

        rows = await self.db.execute(
            select(
                func.date_trunc("month", Transaction.date).label("month_start"),
                func.coalesce(
                    func.sum(case((Transaction.type == "REVENUE", Transaction.amount), else_=0)),
                    0,
                ).label("revenue_total"),
                func.coalesce(
                    func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0)),
                    0,
                ).label("expense_total"),
            )
            .where(
                Transaction.org_id == org_id,
                Transaction.location_id == location_id,
            )
            .group_by("month_start")
            .order_by(func.date_trunc("month", Transaction.date).desc())
            .limit(months)
        )
        out: list[MonthlyAggregate] = []
        for month_start, revenue_total, expense_total in rows.all():
            out.append(
                MonthlyAggregate(
                    org_id=org_id,
                    year_month=month_start.date(),
                    revenue_total=Decimal(revenue_total or 0),
                    expense_total=Decimal(expense_total or 0),
                    net_total=Decimal(revenue_total or 0) - Decimal(expense_total or 0),
                )
            )
        return out

    async def alerts_open_count(self, org_id: uuid.UUID) -> int:
        c = await self.db.scalar(
            select(func.count()).select_from(Alert).where(Alert.org_id == org_id, Alert.status == "OPEN")
        )
        return int(c or 0)

    async def location_benchmark(self, org_id: uuid.UUID, from_date: date, to_date: date) -> dict:
        rows = await self.db.execute(
            select(
                Transaction.location_id.label("location_id"),
                func.coalesce(Location.name, "Unassigned").label("location_name"),
                func.coalesce(
                    func.sum(case((Transaction.type == "REVENUE", Transaction.amount), else_=0)),
                    0,
                ).label("revenue"),
                func.coalesce(
                    func.sum(case((Transaction.type == "EXPENSE", Transaction.amount), else_=0)),
                    0,
                ).label("expense"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .select_from(Transaction)
            .outerjoin(Location, and_(Location.id == Transaction.location_id, Location.org_id == org_id))
            .where(
                Transaction.org_id == org_id,
                Transaction.date >= from_date,
                Transaction.date <= to_date,
            )
            .group_by(Transaction.location_id, Location.name)
            .order_by(func.coalesce(func.sum(Transaction.amount), 0).desc())
        )

        items: list[dict] = []
        total_revenue = Decimal("0")
        total_expense = Decimal("0")
        for row in rows:
            revenue = Decimal(str(row.revenue or 0))
            expense = Decimal(str(row.expense or 0))
            net = revenue - expense
            total_revenue += revenue
            total_expense += expense
            margin_pct = ((net / revenue) * Decimal("100")) if revenue > 0 else None
            items.append(
                {
                    "location_id": row.location_id,
                    "location_name": row.location_name,
                    "transaction_count": int(row.transaction_count or 0),
                    "revenue": revenue,
                    "expense": expense,
                    "net": net,
                    "margin_pct": margin_pct,
                }
            )

        for item in items:
            item["revenue_share_pct"] = (
                (item["revenue"] / total_revenue * Decimal("100")) if total_revenue > 0 else None
            )
            item["expense_share_pct"] = (
                (item["expense"] / total_expense * Decimal("100")) if total_expense > 0 else None
            )

        return {
            "org_id": org_id,
            "from_date": from_date,
            "to_date": to_date,
            "totals": {
                "revenue": total_revenue,
                "expense": total_expense,
                "net": total_revenue - total_expense,
            },
            "locations": items,
        }

    async def runway_threshold_days(self, org_id: uuid.UUID) -> int:
        threshold = await self.db.scalar(
            select(OrganizationSetting.runway_alert_threshold_days).where(OrganizationSetting.org_id == org_id)
        )
        return int(threshold or 60)

    async def transaction_month_starts(
        self,
        org_id: uuid.UUID,
        *,
        location_id: uuid.UUID | None = None,
    ) -> list[date]:
        filters = [Transaction.org_id == org_id]
        if location_id is not None:
            filters.append(Transaction.location_id == location_id)
        q = await self.db.execute(
            select(func.date_trunc("month", Transaction.date))
            .where(and_(*filters))
            .group_by(func.date_trunc("month", Transaction.date))
            .order_by(func.date_trunc("month", Transaction.date))
        )
        return [row[0].date() for row in q.all()]
