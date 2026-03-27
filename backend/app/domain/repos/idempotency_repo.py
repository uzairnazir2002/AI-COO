import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.idempotency_key import IdempotencyKey


class IdempotencyRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        endpoint: str,
        idempotency_key: str,
        now: datetime,
    ) -> IdempotencyKey | None:
        return await self.db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.org_id == org_id,
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.endpoint == endpoint,
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.expires_at > now,
            )
        )

    async def upsert_completed(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        endpoint: str,
        idempotency_key: str,
        request_hash: str,
        status_code: int,
        response_json: dict,
        expires_at: datetime,
    ) -> None:
        stmt = insert(IdempotencyKey).values(
            org_id=org_id,
            user_id=user_id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status_code=status_code,
            response_json=response_json,
            expires_at=expires_at,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_idempotency_scope_key",
            set_={
                "request_hash": request_hash,
                "status_code": status_code,
                "response_json": response_json,
                "expires_at": expires_at,
            },
        )
        await self.db.execute(stmt)
