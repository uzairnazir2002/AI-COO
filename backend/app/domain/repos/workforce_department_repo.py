from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_department import WorkforceDepartment


class WorkforceDepartmentRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool = False) -> list[WorkforceDepartment]:
        query = select(WorkforceDepartment).where(WorkforceDepartment.org_id == org_id)
        if not include_inactive:
            query = query.where(WorkforceDepartment.is_active.is_(True))
        query = query.order_by(WorkforceDepartment.name.asc())
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def get_by_id(self, *, org_id: uuid.UUID, department_id: uuid.UUID) -> WorkforceDepartment | None:
        row = await self.db.execute(
            select(WorkforceDepartment).where(
                WorkforceDepartment.org_id == org_id, WorkforceDepartment.id == department_id
            )
        )
        return row.scalar_one_or_none()

    async def get_by_name_or_code(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        code: str | None,
        exclude_department_id: uuid.UUID | None = None,
    ) -> WorkforceDepartment | None:
        filters = [WorkforceDepartment.org_id == org_id, or_(WorkforceDepartment.name == name, WorkforceDepartment.code == code)]
        if code is None:
            filters = [WorkforceDepartment.org_id == org_id, WorkforceDepartment.name == name]
        if exclude_department_id:
            filters.append(WorkforceDepartment.id != exclude_department_id)
        row = await self.db.execute(select(WorkforceDepartment).where(and_(*filters)))
        return row.scalar_one_or_none()

    async def create(self, row: WorkforceDepartment) -> WorkforceDepartment:
        self.db.add(row)
        await self.db.flush()
        return row

