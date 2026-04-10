from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_leave_balance import WorkforceLeaveBalance


class WorkforceLeaveBalanceRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID,
        leave_type_id: uuid.UUID,
        year: int,
    ) -> WorkforceLeaveBalance | None:
        rows = await self.db.execute(
            select(WorkforceLeaveBalance).where(
                WorkforceLeaveBalance.org_id == org_id,
                WorkforceLeaveBalance.employee_id == employee_id,
                WorkforceLeaveBalance.leave_type_id == leave_type_id,
                WorkforceLeaveBalance.year == int(year),
            )
        )
        return rows.scalar_one_or_none()

    async def list_by_org(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        year: int | None = None,
        limit: int = 1000,
    ) -> list[WorkforceLeaveBalance]:
        q = select(WorkforceLeaveBalance).where(WorkforceLeaveBalance.org_id == org_id)
        if employee_id is not None:
            q = q.where(WorkforceLeaveBalance.employee_id == employee_id)
        if year is not None:
            q = q.where(WorkforceLeaveBalance.year == int(year))
        q = q.order_by(WorkforceLeaveBalance.employee_id.asc(), WorkforceLeaveBalance.year.desc()).limit(
            max(1, min(int(limit), 5000))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def upsert(self, row: WorkforceLeaveBalance) -> WorkforceLeaveBalance:
        self.db.add(row)
        await self.db.flush()
        return row

