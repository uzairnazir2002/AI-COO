from __future__ import annotations

import uuid

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_title import WorkforceTitle


class WorkforceTitleRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(self, org_id: uuid.UUID, *, include_inactive: bool = False) -> list[WorkforceTitle]:
        query = select(WorkforceTitle).where(WorkforceTitle.org_id == org_id)
        if not include_inactive:
            query = query.where(WorkforceTitle.is_active.is_(True))
        query = query.order_by(WorkforceTitle.name.asc())
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def get_by_id(self, *, org_id: uuid.UUID, title_id: uuid.UUID) -> WorkforceTitle | None:
        row = await self.db.execute(
            select(WorkforceTitle).where(WorkforceTitle.org_id == org_id, WorkforceTitle.id == title_id)
        )
        return row.scalar_one_or_none()

    async def get_by_name(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        exclude_title_id: uuid.UUID | None = None,
    ) -> WorkforceTitle | None:
        filters = [WorkforceTitle.org_id == org_id, WorkforceTitle.name == name]
        if exclude_title_id:
            filters.append(WorkforceTitle.id != exclude_title_id)
        row = await self.db.execute(select(WorkforceTitle).where(and_(*filters)))
        return row.scalar_one_or_none()

    async def create(self, row: WorkforceTitle) -> WorkforceTitle:
        self.db.add(row)
        await self.db.flush()
        return row

