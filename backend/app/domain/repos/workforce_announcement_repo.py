from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_announcement import WorkforceAnnouncement
from app.domain.models.workforce_announcement_receipt import WorkforceAnnouncementReceipt


class WorkforceAnnouncementRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def exists_automation_dedupe(self, *, org_id: uuid.UUID, key: str) -> bool:
        k = (key or "").strip()
        if not k:
            return False
        rows = await self.db.execute(
            select(WorkforceAnnouncement.id).where(
                WorkforceAnnouncement.org_id == org_id,
                WorkforceAnnouncement.automation_dedupe_key == k,
            )
        )
        return rows.scalar_one_or_none() is not None

    async def get_by_id(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID) -> WorkforceAnnouncement | None:
        rows = await self.db.execute(
            select(WorkforceAnnouncement).where(
                WorkforceAnnouncement.org_id == org_id, WorkforceAnnouncement.id == announcement_id
            )
        )
        return rows.scalar_one_or_none()

    async def list_editor_view(
        self,
        *,
        org_id: uuid.UUID,
        include_archived: bool,
        limit: int = 200,
    ) -> list[WorkforceAnnouncement]:
        q = select(WorkforceAnnouncement).where(WorkforceAnnouncement.org_id == org_id)
        if not include_archived:
            q = q.where(WorkforceAnnouncement.status != "ARCHIVED")
        q = q.order_by(
            desc(WorkforceAnnouncement.pinned),
            desc(WorkforceAnnouncement.published_at),
            desc(WorkforceAnnouncement.created_at),
        ).limit(max(1, min(limit, 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def list_published_visible(
        self,
        *,
        org_id: uuid.UUID,
        as_of: date,
        limit: int = 200,
    ) -> list[WorkforceAnnouncement]:
        q = (
            select(WorkforceAnnouncement)
            .where(
                WorkforceAnnouncement.org_id == org_id,
                WorkforceAnnouncement.status == "PUBLISHED",
                WorkforceAnnouncement.published_at.is_not(None),
                or_(WorkforceAnnouncement.expires_at.is_(None), WorkforceAnnouncement.expires_at >= as_of),
            )
            .order_by(desc(WorkforceAnnouncement.pinned), desc(WorkforceAnnouncement.published_at))
            .limit(max(1, min(limit, 500)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def list_due_scheduled(self, *, now: datetime, limit: int = 50) -> list[WorkforceAnnouncement]:
        q = (
            select(WorkforceAnnouncement)
            .where(
                WorkforceAnnouncement.status == "DRAFT",
                WorkforceAnnouncement.scheduled_publish_at.is_not(None),
                WorkforceAnnouncement.scheduled_publish_at <= now,
            )
            .order_by(WorkforceAnnouncement.scheduled_publish_at.asc())
            .limit(max(1, min(limit, 200)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def create(self, row: WorkforceAnnouncement) -> WorkforceAnnouncement:
        self.db.add(row)
        await self.db.flush()
        return row

    async def update(self, row: WorkforceAnnouncement) -> WorkforceAnnouncement:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_receipt(
        self, *, announcement_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkforceAnnouncementReceipt | None:
        rows = await self.db.execute(
            select(WorkforceAnnouncementReceipt).where(
                WorkforceAnnouncementReceipt.announcement_id == announcement_id,
                WorkforceAnnouncementReceipt.user_id == user_id,
            )
        )
        return rows.scalar_one_or_none()

    async def upsert_receipt_read(self, *, announcement_id: uuid.UUID, user_id: uuid.UUID) -> WorkforceAnnouncementReceipt:
        row = await self.get_receipt(announcement_id=announcement_id, user_id=user_id)
        now = datetime.now(tz=timezone.utc)
        if row is None:
            row = WorkforceAnnouncementReceipt(
                announcement_id=announcement_id,
                user_id=user_id,
                read_at=now,
            )
            self.db.add(row)
        elif row.read_at is None:
            row.read_at = now
            self.db.add(row)
        await self.db.flush()
        return row

    async def upsert_receipt_ack(self, *, announcement_id: uuid.UUID, user_id: uuid.UUID) -> WorkforceAnnouncementReceipt:
        row = await self.get_receipt(announcement_id=announcement_id, user_id=user_id)
        now = datetime.now(tz=timezone.utc)
        if row is None:
            row = WorkforceAnnouncementReceipt(
                announcement_id=announcement_id,
                user_id=user_id,
                read_at=now,
                acknowledged_at=now,
            )
            self.db.add(row)
        else:
            if row.read_at is None:
                row.read_at = now
            row.acknowledged_at = now
            self.db.add(row)
        await self.db.flush()
        return row
