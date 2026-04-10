from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_payroll_adjustment import WorkforcePayrollAdjustment
from app.domain.models.workforce_payroll_entry import WorkforcePayrollEntry
from app.domain.models.workforce_payroll_period import WorkforcePayrollPeriod


class WorkforcePayrollRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Periods
    async def list_periods(self, *, org_id: uuid.UUID, limit: int = 50) -> list[WorkforcePayrollPeriod]:
        q = (
            select(WorkforcePayrollPeriod)
            .where(WorkforcePayrollPeriod.org_id == org_id)
            .order_by(WorkforcePayrollPeriod.start_date.desc())
            .limit(max(1, min(int(limit), 200)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_period(self, *, org_id: uuid.UUID, period_id: uuid.UUID) -> WorkforcePayrollPeriod | None:
        rows = await self.db.execute(
            select(WorkforcePayrollPeriod).where(
                WorkforcePayrollPeriod.org_id == org_id, WorkforcePayrollPeriod.id == period_id
            )
        )
        return rows.scalar_one_or_none()

    async def create_period(self, row: WorkforcePayrollPeriod) -> WorkforcePayrollPeriod:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update_period(self, row: WorkforcePayrollPeriod) -> WorkforcePayrollPeriod:
        self.db.add(row)
        await self.db.flush()
        return row

    # Entries
    async def list_entries(self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, limit: int = 5000) -> list[WorkforcePayrollEntry]:
        q = (
            select(WorkforcePayrollEntry)
            .where(
                WorkforcePayrollEntry.org_id == org_id,
                WorkforcePayrollEntry.payroll_period_id == payroll_period_id,
            )
            .order_by(WorkforcePayrollEntry.employee_id.asc())
            .limit(max(1, min(int(limit), 5000)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_entry(self, *, org_id: uuid.UUID, entry_id: uuid.UUID) -> WorkforcePayrollEntry | None:
        rows = await self.db.execute(
            select(WorkforcePayrollEntry).where(WorkforcePayrollEntry.org_id == org_id, WorkforcePayrollEntry.id == entry_id)
        )
        return rows.scalar_one_or_none()

    async def get_entry_for_employee(
        self, *, org_id: uuid.UUID, payroll_period_id: uuid.UUID, employee_id: uuid.UUID
    ) -> WorkforcePayrollEntry | None:
        rows = await self.db.execute(
            select(WorkforcePayrollEntry).where(
                WorkforcePayrollEntry.org_id == org_id,
                WorkforcePayrollEntry.payroll_period_id == payroll_period_id,
                WorkforcePayrollEntry.employee_id == employee_id,
            )
        )
        return rows.scalar_one_or_none()

    async def upsert_entry(self, row: WorkforcePayrollEntry) -> WorkforcePayrollEntry:
        self.db.add(row)
        await self.db.flush()
        return row

    # Adjustments
    async def list_adjustments(self, *, org_id: uuid.UUID, payroll_entry_id: uuid.UUID, limit: int = 500) -> list[WorkforcePayrollAdjustment]:
        q = (
            select(WorkforcePayrollAdjustment)
            .where(WorkforcePayrollAdjustment.org_id == org_id, WorkforcePayrollAdjustment.payroll_entry_id == payroll_entry_id)
            .order_by(WorkforcePayrollAdjustment.created_at.asc())
            .limit(max(1, min(int(limit), 500)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def create_adjustment(self, row: WorkforcePayrollAdjustment) -> WorkforcePayrollAdjustment:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_adjustment(self, *, org_id: uuid.UUID, adjustment_id: uuid.UUID) -> WorkforcePayrollAdjustment | None:
        rows = await self.db.execute(
            select(WorkforcePayrollAdjustment).where(
                WorkforcePayrollAdjustment.org_id == org_id, WorkforcePayrollAdjustment.id == adjustment_id
            )
        )
        return rows.scalar_one_or_none()

    async def delete_adjustment(self, row: WorkforcePayrollAdjustment) -> None:
        await self.db.delete(row)

    # Convenience for attendance range queries
    async def attendance_sum_for_employee(
        self,
        *,
        attendance_repo,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> tuple[int, int]:
        rows = await attendance_repo.list_records(org_id=org_id, from_date=start_date, to_date=end_date, employee_id=employee_id, limit=5000)
        worked = 0
        overtime = 0
        for r in rows:
            worked += int(getattr(r, "worked_minutes", 0) or 0)
            overtime += int(getattr(r, "overtime_minutes", 0) or 0)
        return worked, overtime

