from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_shift import WorkforceShift
from app.domain.models.workforce_shift_assignment import WorkforceShiftAssignment


class WorkforceShiftRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_shifts(self, *, org_id: uuid.UUID, include_inactive: bool = False) -> list[WorkforceShift]:
        q = select(WorkforceShift).where(WorkforceShift.org_id == org_id)
        if not include_inactive:
            q = q.where(WorkforceShift.is_active.is_(True))
        q = q.order_by(WorkforceShift.name.asc())
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_shift(self, *, org_id: uuid.UUID, shift_id: uuid.UUID) -> WorkforceShift | None:
        row = await self.db.execute(
            select(WorkforceShift).where(WorkforceShift.org_id == org_id, WorkforceShift.id == shift_id)
        )
        return row.scalar_one_or_none()

    async def get_shift_by_name(
        self, *, org_id: uuid.UUID, name: str, exclude_shift_id: uuid.UUID | None = None
    ) -> WorkforceShift | None:
        filters = [WorkforceShift.org_id == org_id, WorkforceShift.name == name]
        if exclude_shift_id:
            filters.append(WorkforceShift.id != exclude_shift_id)
        row = await self.db.execute(select(WorkforceShift).where(and_(*filters)))
        return row.scalar_one_or_none()

    async def create_shift(self, row: WorkforceShift) -> WorkforceShift:
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_assignments(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        shift_id: uuid.UUID | None = None,
        as_of: date | None = None,
        limit: int = 200,
    ) -> list[WorkforceShiftAssignment]:
        q = select(WorkforceShiftAssignment).where(WorkforceShiftAssignment.org_id == org_id)
        if employee_id is not None:
            q = q.where(WorkforceShiftAssignment.employee_id == employee_id)
        if shift_id is not None:
            q = q.where(WorkforceShiftAssignment.shift_id == shift_id)
        if as_of is not None:
            q = q.where(WorkforceShiftAssignment.effective_from <= as_of).where(
                (WorkforceShiftAssignment.effective_to.is_(None)) | (WorkforceShiftAssignment.effective_to >= as_of)
            )
        q = q.order_by(WorkforceShiftAssignment.effective_from.desc()).limit(max(1, min(int(limit), 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_assignment(self, *, org_id: uuid.UUID, assignment_id: uuid.UUID) -> WorkforceShiftAssignment | None:
        row = await self.db.execute(
            select(WorkforceShiftAssignment).where(
                WorkforceShiftAssignment.org_id == org_id, WorkforceShiftAssignment.id == assignment_id
            )
        )
        return row.scalar_one_or_none()

    async def create_assignment(self, row: WorkforceShiftAssignment) -> WorkforceShiftAssignment:
        self.db.add(row)
        await self.db.flush()
        return row

