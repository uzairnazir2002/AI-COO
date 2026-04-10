from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_announcement_delivery import WorkforceAnnouncementDelivery


class WorkforceAnnouncementDeliveryRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_announcement(
        self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, limit: int = 500
    ) -> list[WorkforceAnnouncementDelivery]:
        rows = await self.db.execute(
            select(WorkforceAnnouncementDelivery)
            .where(
                WorkforceAnnouncementDelivery.org_id == org_id,
                WorkforceAnnouncementDelivery.announcement_id == announcement_id,
            )
            .order_by(desc(WorkforceAnnouncementDelivery.created_at))
            .limit(max(1, min(limit, 2000)))
        )
        return list(rows.scalars().all())

    async def list_for_announcement_page(
        self,
        *,
        org_id: uuid.UUID,
        announcement_id: uuid.UUID,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[WorkforceAnnouncementDelivery], int]:
        ps = max(1, min(int(page_size), 200))
        p = max(1, int(page))
        filters = [
            WorkforceAnnouncementDelivery.org_id == org_id,
            WorkforceAnnouncementDelivery.announcement_id == announcement_id,
        ]
        if status and status.strip().upper() not in {"", "ALL"}:
            filters.append(WorkforceAnnouncementDelivery.status == status.strip().upper())
        count_q = await self.db.execute(
            select(func.count()).select_from(WorkforceAnnouncementDelivery).where(*filters)
        )
        total = int(count_q.scalar_one() or 0)
        rows = await self.db.execute(
            select(WorkforceAnnouncementDelivery)
            .where(*filters)
            .order_by(desc(WorkforceAnnouncementDelivery.created_at))
            .offset((p - 1) * ps)
            .limit(ps)
        )
        return list(rows.scalars().all()), total

    async def create(self, row: WorkforceAnnouncementDelivery) -> WorkforceAnnouncementDelivery:
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_by_id(self, *, delivery_id: uuid.UUID) -> WorkforceAnnouncementDelivery | None:
        rows = await self.db.execute(select(WorkforceAnnouncementDelivery).where(WorkforceAnnouncementDelivery.id == delivery_id))
        return rows.scalar_one_or_none()

    async def mark_sent(self, *, delivery_id: uuid.UUID, outbox_event_id: uuid.UUID | None = None) -> None:
        row = await self.get_by_id(delivery_id=delivery_id)
        if row is None:
            return
        row.status = "SENT"
        row.sent_at = datetime.now(tz=timezone.utc)
        row.error = None
        if outbox_event_id is not None:
            row.outbox_event_id = outbox_event_id
        self.db.add(row)
        await self.db.flush()

    async def mark_failed(self, *, delivery_id: uuid.UUID, error: str) -> None:
        row = await self.get_by_id(delivery_id=delivery_id)
        if row is None:
            return
        row.status = "FAILED"
        row.error = (error or "")[:4000]
        self.db.add(row)
        await self.db.flush()

    async def mark_retrying(self, *, delivery_id: uuid.UUID, error: str | None = None) -> None:
        row = await self.get_by_id(delivery_id=delivery_id)
        if row is None:
            return
        row.status = "RETRYING"
        if error:
            row.error = (error or "")[:4000]
        self.db.add(row)
        await self.db.flush()

    async def attach_outbox(self, *, delivery_id: uuid.UUID, outbox_event_id: uuid.UUID) -> None:
        row = await self.get_by_id(delivery_id=delivery_id)
        if row is None:
            return
        row.outbox_event_id = outbox_event_id
        self.db.add(row)
        await self.db.flush()
