import uuid
from datetime import timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repos.dead_letter_repo import DeadLetterRepo
from app.domain.models.outbox_event import OutboxEvent
from app.utils.time import utc_now


class OutboxRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(
        self,
        *,
        event_type: str,
        payload: dict,
        org_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        dedupe_key: str | None = None,
        max_attempts: int = 5,
    ) -> OutboxEvent:
        event = OutboxEvent(
            org_id=org_id,
            event_type=event_type,
            payload=payload,
            status="PENDING",
            attempts=0,
            max_attempts=max_attempts,
            available_at=utc_now(),
            correlation_id=correlation_id,
            dedupe_key=dedupe_key,
        )
        async with self.db.begin_nested():
            self.db.add(event)
            try:
                await self.db.flush()
                return event
            except IntegrityError:
                if not dedupe_key:
                    raise
        q = await self.db.execute(
            select(OutboxEvent).where(OutboxEvent.dedupe_key == dedupe_key)
        )
        existing = q.scalar_one_or_none()
        if not existing:
            raise RuntimeError("Outbox dedupe insert failed but existing event not found")
        return existing

    async def claim_pending(self, *, limit: int = 100) -> list[OutboxEvent]:
        now = utc_now()
        stmt: Select[tuple[OutboxEvent]] = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status.in_(["PENDING", "RETRYING"]),
                OutboxEvent.available_at <= now,
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = await self.db.execute(stmt)
        events = list(rows.scalars().all())
        for ev in events:
            ev.status = "PROCESSING"
        await self.db.flush()
        return events

    async def mark_sent(self, event: OutboxEvent) -> None:
        event.status = "SENT"
        event.sent_at = utc_now()
        event.last_error = None
        await self.db.flush()

    async def mark_retry_or_failed(self, event: OutboxEvent, error: str) -> None:
        event.attempts += 1
        event.last_error = error[:2000]
        if event.attempts >= event.max_attempts:
            event.status = "FAILED"
            await DeadLetterRepo(self.db).record_failure(
                org_id=event.org_id,
                source_type="OUTBOX",
                source_id=event.id,
                source_task_id=None,
                source_name=event.event_type,
                attempts=event.attempts,
                last_error=event.last_error,
                payload=event.payload,
                metadata_json={"max_attempts": event.max_attempts},
            )
        else:
            event.status = "RETRYING"
            delay_seconds = min(300, 2 ** event.attempts)
            event.available_at = utc_now() + timedelta(seconds=delay_seconds)
        await self.db.flush()

    async def requeue(self, event: OutboxEvent, *, reset_attempts: bool = False) -> OutboxEvent:
        event.status = "PENDING"
        event.available_at = utc_now()
        event.last_error = None
        event.sent_at = None
        if reset_attempts:
            event.attempts = 0
        await self.db.flush()
        return event

    async def by_id(self, event_id: uuid.UUID) -> OutboxEvent | None:
        q = await self.db.execute(select(OutboxEvent).where(OutboxEvent.id == event_id))
        return q.scalar_one_or_none()

    async def list_events(
        self,
        *,
        org_id: uuid.UUID | None,
        status: str | None,
        event_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[OutboxEvent], int]:
        stmt = select(OutboxEvent)
        count_stmt = select(func.count()).select_from(OutboxEvent)

        if org_id is None:
            stmt = stmt.where(OutboxEvent.org_id.is_(None))
            count_stmt = count_stmt.where(OutboxEvent.org_id.is_(None))
        else:
            stmt = stmt.where(OutboxEvent.org_id == org_id)
            count_stmt = count_stmt.where(OutboxEvent.org_id == org_id)

        if status:
            stmt = stmt.where(OutboxEvent.status == status)
            count_stmt = count_stmt.where(OutboxEvent.status == status)
        if event_type:
            stmt = stmt.where(OutboxEvent.event_type == event_type)
            count_stmt = count_stmt.where(OutboxEvent.event_type == event_type)

        stmt = stmt.order_by(OutboxEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(stmt)).scalars().all())
        total = int((await self.db.execute(count_stmt)).scalar_one())
        return items, total

    async def counts_by_status(self, *, org_id: uuid.UUID | None) -> dict[str, int]:
        stmt = select(OutboxEvent.status, func.count()).group_by(OutboxEvent.status)
        if org_id is None:
            stmt = stmt.where(OutboxEvent.org_id.is_(None))
        else:
            stmt = stmt.where(OutboxEvent.org_id == org_id)
        rows = (await self.db.execute(stmt)).all()
        return {str(status): int(count) for status, count in rows}
