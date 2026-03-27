from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.monthly_aggregate import MonthlyAggregate
from app.domain.models.transaction import Transaction
from app.utils.time import month_start, utc_now


class TransactionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, tx: Transaction) -> Transaction:
        self.db.add(tx)
        await self.db.flush()
        return tx

    async def get_by_id_org(self, tx_id: uuid.UUID, org_id: uuid.UUID) -> Transaction | None:
        q = await self.db.execute(select(Transaction).where(Transaction.id == tx_id, Transaction.org_id == org_id))
        return q.scalar_one_or_none()

    async def delete(self, tx: Transaction) -> None:
        await self.db.delete(tx)

    async def list(
        self,
        org_id: uuid.UUID,
        location_id: uuid.UUID | None,
        date_from: date | None,
        date_to: date | None,
        tx_type: str | None,
        category: str | None,
        q: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Transaction], int]:
        filters = [Transaction.org_id == org_id]
        if location_id:
            filters.append(Transaction.location_id == location_id)
        if date_from:
            filters.append(Transaction.date >= date_from)
        if date_to:
            filters.append(Transaction.date <= date_to)
        if tx_type:
            filters.append(Transaction.type == tx_type)
        if category:
            filters.append(Transaction.category == category)
        if q:
            filters.append(
                or_(
                    Transaction.vendor.ilike(f"%{q}%"),
                    Transaction.notes.ilike(f"%{q}%"),
                    Transaction.category.ilike(f"%{q}%"),
                )
            )

        query = select(Transaction).where(and_(*filters)).order_by(Transaction.date.desc())
        total_q = select(func.count()).select_from(Transaction).where(and_(*filters))
        res = await self.db.execute(query.offset((page - 1) * page_size).limit(page_size))
        total = await self.db.scalar(total_q)
        return list(res.scalars().all()), int(total or 0)

    async def duplicate_count(self, org_id: uuid.UUID, txs: list[dict]) -> int:
        count = 0
        for r in txs:
            q = await self.db.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(
                    Transaction.org_id == org_id,
                    Transaction.date == r["date"],
                    Transaction.amount == r["amount"],
                    Transaction.type == r["type"],
                    Transaction.category == r["category"],
                    Transaction.location_id == r.get("location_id"),
                    Transaction.vendor == r["vendor"],
                )
            )
            count += int(q or 0)
        return count

    async def existing_duplicate_keys(self, org_id: uuid.UUID, txs: list[dict]) -> set[tuple]:
        if not txs:
            return set()
        dates = [r["date"] for r in txs]
        min_date = min(dates)
        max_date = max(dates)
        rows = await self.db.execute(
            select(
                Transaction.date,
                Transaction.amount,
                Transaction.type,
                Transaction.category,
                Transaction.location_id,
                Transaction.vendor,
            ).where(
                Transaction.org_id == org_id,
                Transaction.date >= min_date,
                Transaction.date <= max_date,
            )
        )
        return {
            (row.date, row.amount, row.type, row.category, row.location_id, row.vendor)
            for row in rows.all()
        }

    async def upsert_monthly_aggregate(self, org_id: uuid.UUID, d: date) -> None:
        ym = month_start(d)
        end = date(ym.year, ym.month, monthrange(ym.year, ym.month)[1])
        revenue = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.date >= ym,
                Transaction.date <= end,
                Transaction.type == "REVENUE",
            )
        )
        expense = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.org_id == org_id,
                Transaction.date >= ym,
                Transaction.date <= end,
                Transaction.type == "EXPENSE",
            )
        )
        agg_q = await self.db.execute(
            select(MonthlyAggregate).where(MonthlyAggregate.org_id == org_id, MonthlyAggregate.year_month == ym)
        )
        agg = agg_q.scalar_one_or_none()
        if agg is None:
            agg = MonthlyAggregate(org_id=org_id, year_month=ym)
            self.db.add(agg)
        agg.revenue_total = revenue or 0
        agg.expense_total = expense or 0
        agg.net_total = (revenue or 0) - (expense or 0)
        agg.updated_at = utc_now()
        await self.db.flush()

    async def bulk_remap_category(
        self,
        org_id: uuid.UUID,
        from_category: str,
        to_category: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> int:
        filters = [Transaction.org_id == org_id, Transaction.category == from_category]
        if from_date:
            filters.append(Transaction.date >= from_date)
        if to_date:
            filters.append(Transaction.date <= to_date)
        rows = await self.db.execute(select(Transaction).where(and_(*filters)))
        txs = list(rows.scalars().all())
        for tx in txs:
            tx.category = to_category
        await self.db.flush()
        return len(txs)

    async def list_month_starts_for_category(
        self,
        org_id: uuid.UUID,
        category: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[date]:
        filters = [Transaction.org_id == org_id, Transaction.category == category]
        if from_date:
            filters.append(Transaction.date >= from_date)
        if to_date:
            filters.append(Transaction.date <= to_date)
        rows = await self.db.execute(select(Transaction.date).where(and_(*filters)))
        month_starts = {month_start(r[0]) for r in rows.all()}
        return sorted(month_starts)
