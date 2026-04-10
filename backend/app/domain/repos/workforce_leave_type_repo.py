from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_leave_type import WorkforceLeaveType


class WorkforceLeaveTypeRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int = 500) -> list[WorkforceLeaveType]:
        q = select(WorkforceLeaveType).where(WorkforceLeaveType.org_id == org_id)
        if not include_inactive:
            q = q.where(WorkforceLeaveType.is_active.is_(True))
        q = q.order_by(WorkforceLeaveType.name.asc()).limit(max(1, min(int(limit), 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_by_id(self, *, org_id: uuid.UUID, leave_type_id: uuid.UUID) -> WorkforceLeaveType | None:
        rows = await self.db.execute(
            select(WorkforceLeaveType).where(WorkforceLeaveType.org_id == org_id, WorkforceLeaveType.id == leave_type_id)
        )
        return rows.scalar_one_or_none()

    async def get_by_name_or_code(
        self, *, org_id: uuid.UUID, name: str, code: str | None
    ) -> WorkforceLeaveType | None:
        q = select(WorkforceLeaveType).where(WorkforceLeaveType.org_id == org_id, WorkforceLeaveType.name == name)
        rows = await self.db.execute(q)
        hit = rows.scalar_one_or_none()
        if hit is not None:
            return hit
        if code is None:
            return None
        rows2 = await self.db.execute(
            select(WorkforceLeaveType).where(WorkforceLeaveType.org_id == org_id, WorkforceLeaveType.code == code)
        )
        return rows2.scalar_one_or_none()

    async def create(self, row: WorkforceLeaveType) -> WorkforceLeaveType:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update(self, row: WorkforceLeaveType) -> WorkforceLeaveType:
        self.db.add(row)
        await self.db.flush()
        return row

