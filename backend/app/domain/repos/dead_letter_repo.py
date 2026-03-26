import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.dead_letter_event import DeadLetterEvent
from app.utils.time import utc_now


class DeadLetterRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_failure(
        self,
        *,
        org_id: uuid.UUID | None,
        source_type: str,
        source_id: uuid.UUID | None,
        source_task_id: str | None,
        source_name: str,
        attempts: int,
        last_error: str | None,
        payload: dict | None,
        metadata_json: dict | None = None,
    ) -> DeadLetterEvent:
        stmt = select(DeadLetterEvent).where(
            DeadLetterEvent.status == "OPEN",
            DeadLetterEvent.source_type == source_type,
            and_(DeadLetterEvent.source_id == source_id) if source_id else DeadLetterEvent.source_id.is_(None),
            and_(DeadLetterEvent.org_id == org_id) if org_id else DeadLetterEvent.org_id.is_(None),
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        now = utc_now()
        if row:
            row.attempts = max(int(attempts or 1), row.attempts)
            row.last_error = (last_error or "")[:2000] if last_error else None
            row.last_failed_at = now
            row.updated_at = now
            row.payload = payload or {}
            if metadata_json:
                merged = dict(row.metadata_json or {})
                merged.update(metadata_json)
                row.metadata_json = merged
            await self.db.flush()
            return row

        row = DeadLetterEvent(
            org_id=org_id,
            source_type=source_type,
            source_id=source_id,
            source_task_id=source_task_id,
            source_name=source_name,
            status="OPEN",
            attempts=max(int(attempts or 1), 1),
            last_error=(last_error or "")[:2000] if last_error else None,
            payload=payload or {},
            metadata_json=metadata_json or {},
            first_failed_at=now,
            last_failed_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def by_id(self, dead_letter_id: uuid.UUID) -> DeadLetterEvent | None:
        return await self.db.scalar(select(DeadLetterEvent).where(DeadLetterEvent.id == dead_letter_id))

    async def list_events(
        self,
        *,
        org_id: uuid.UUID,
        status: str | None,
        source_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[DeadLetterEvent], int]:
        stmt = select(DeadLetterEvent).where(DeadLetterEvent.org_id == org_id)
        count_stmt = select(func.count()).select_from(DeadLetterEvent).where(DeadLetterEvent.org_id == org_id)
        if status:
            stmt = stmt.where(DeadLetterEvent.status == status)
            count_stmt = count_stmt.where(DeadLetterEvent.status == status)
        if source_type:
            stmt = stmt.where(DeadLetterEvent.source_type == source_type)
            count_stmt = count_stmt.where(DeadLetterEvent.source_type == source_type)
        stmt = stmt.order_by(DeadLetterEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return rows, total

    async def counts_by_status(self, *, org_id: uuid.UUID) -> dict[str, int]:
        rows = (
            await self.db.execute(
                select(DeadLetterEvent.status, func.count())
                .where(DeadLetterEvent.org_id == org_id)
                .group_by(DeadLetterEvent.status)
            )
        ).all()
        return {str(status): int(count) for status, count in rows}

    async def open_count(self, *, org_id: uuid.UUID) -> int:
        count = await self.db.scalar(
            select(func.count()).select_from(DeadLetterEvent).where(
                DeadLetterEvent.org_id == org_id,
                DeadLetterEvent.status == "OPEN",
            )
        )
        return int(count or 0)

    async def mark_replayed(self, event: DeadLetterEvent, *, metadata_json: dict | None = None) -> DeadLetterEvent:
        event.status = "REPLAYED"
        event.replayed_at = utc_now()
        if metadata_json:
            merged = dict(event.metadata_json or {})
            merged.update(metadata_json)
            event.metadata_json = merged
        event.updated_at = utc_now()
        await self.db.flush()
        return event

    async def mark_dismissed(self, event: DeadLetterEvent, *, reason: str | None = None) -> DeadLetterEvent:
        event.status = "DISMISSED"
        meta = dict(event.metadata_json or {})
        if reason:
            meta["dismiss_reason"] = reason
        event.metadata_json = meta
        event.updated_at = utc_now()
        await self.db.flush()
        return event
