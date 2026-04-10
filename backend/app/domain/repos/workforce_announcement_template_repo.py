from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_announcement_template import WorkforceAnnouncementTemplate


class WorkforceAnnouncementTemplateRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_org(self, *, org_id: uuid.UUID, include_inactive: bool = False, limit: int = 200) -> list[WorkforceAnnouncementTemplate]:
        q = select(WorkforceAnnouncementTemplate).where(WorkforceAnnouncementTemplate.org_id == org_id)
        if not include_inactive:
            q = q.where(WorkforceAnnouncementTemplate.is_active.is_(True))
        q = q.order_by(desc(WorkforceAnnouncementTemplate.created_at)).limit(max(1, min(limit, 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_by_id(self, *, org_id: uuid.UUID, template_id: uuid.UUID) -> WorkforceAnnouncementTemplate | None:
        rows = await self.db.execute(
            select(WorkforceAnnouncementTemplate).where(
                WorkforceAnnouncementTemplate.org_id == org_id, WorkforceAnnouncementTemplate.id == template_id
            )
        )
        return rows.scalar_one_or_none()

    async def get_active_by_automation_key(
        self, *, org_id: uuid.UUID, automation_key: str
    ) -> WorkforceAnnouncementTemplate | None:
        k = (automation_key or "").strip()
        if not k:
            return None
        rows = await self.db.execute(
            select(WorkforceAnnouncementTemplate)
            .where(
                WorkforceAnnouncementTemplate.org_id == org_id,
                WorkforceAnnouncementTemplate.automation_key == k,
                WorkforceAnnouncementTemplate.is_active.is_(True),
            )
            .order_by(desc(WorkforceAnnouncementTemplate.created_at))
            .limit(1)
        )
        return rows.scalar_one_or_none()

    async def get_by_code(self, *, org_id: uuid.UUID, code: str) -> WorkforceAnnouncementTemplate | None:
        c = (code or "").strip()
        if not c:
            return None
        rows = await self.db.execute(
            select(WorkforceAnnouncementTemplate).where(
                WorkforceAnnouncementTemplate.org_id == org_id,
                WorkforceAnnouncementTemplate.code == c,
            )
        )
        return rows.scalar_one_or_none()

    async def create(self, row: WorkforceAnnouncementTemplate) -> WorkforceAnnouncementTemplate:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update(self, row: WorkforceAnnouncementTemplate) -> WorkforceAnnouncementTemplate:
        self.db.add(row)
        await self.db.flush()
        return row
