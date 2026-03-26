import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.deletion_request import DeletionRequest


class DeletionRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_request(
        self,
        *,
        scope: str,
        requested_by_user_id: uuid.UUID | None,
        target_user_id: uuid.UUID | None,
        target_org_id: uuid.UUID | None,
        reason: str | None,
        delete_after: datetime,
    ) -> DeletionRequest:
        row = DeletionRequest(
            scope=scope,
            status="PENDING",
            requested_by_user_id=requested_by_user_id,
            target_user_id=target_user_id,
            target_org_id=target_org_id,
            reason=reason,
            delete_after=delete_after,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def latest_pending_for_user(self, user_id: uuid.UUID) -> DeletionRequest | None:
        q = await self.db.execute(
            select(DeletionRequest)
            .where(
                DeletionRequest.scope == "USER",
                DeletionRequest.target_user_id == user_id,
                DeletionRequest.status == "PENDING",
            )
            .order_by(DeletionRequest.created_at.desc())
            .limit(1)
        )
        return q.scalar_one_or_none()

    async def latest_pending_for_org(self, org_id: uuid.UUID) -> DeletionRequest | None:
        q = await self.db.execute(
            select(DeletionRequest)
            .where(
                DeletionRequest.scope == "ORG",
                DeletionRequest.target_org_id == org_id,
                DeletionRequest.status == "PENDING",
            )
            .order_by(DeletionRequest.created_at.desc())
            .limit(1)
        )
        return q.scalar_one_or_none()

    async def due_requests(self, now: datetime, limit: int = 100) -> list[DeletionRequest]:
        q = await self.db.execute(
            select(DeletionRequest)
            .where(
                DeletionRequest.status == "PENDING",
                DeletionRequest.delete_after <= now,
            )
            .order_by(DeletionRequest.delete_after.asc())
            .limit(limit)
        )
        return list(q.scalars().all())

    async def mark_processed(self, row: DeletionRequest, *, processed_at: datetime) -> None:
        row.status = "PROCESSED"
        row.processed_at = processed_at
        await self.db.flush()

    async def list_for_user(self, user_id: uuid.UUID, *, limit: int = 20) -> list[DeletionRequest]:
        q = await self.db.execute(
            select(DeletionRequest)
            .where(
                DeletionRequest.scope == "USER",
                DeletionRequest.target_user_id == user_id,
            )
            .order_by(DeletionRequest.created_at.desc())
            .limit(limit)
        )
        return list(q.scalars().all())

    async def list_for_org(self, org_id: uuid.UUID, *, limit: int = 50) -> list[DeletionRequest]:
        q = await self.db.execute(
            select(DeletionRequest)
            .where(
                DeletionRequest.scope == "ORG",
                DeletionRequest.target_org_id == org_id,
            )
            .order_by(DeletionRequest.created_at.desc())
            .limit(limit)
        )
        return list(q.scalars().all())
