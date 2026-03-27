import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.audit_log import AuditLog


class AuditRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        actor_user_id: uuid.UUID | None,
        org_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata_json: dict,
    ) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                org_id=org_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_json=metadata_json,
            )
        )
        await self.db.flush()

    async def list_entity_events(
        self,
        *,
        org_id: uuid.UUID,
        entity_type: str,
        entity_id: str,
        actions: list[str] | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        q = (
            select(AuditLog)
            .where(
                AuditLog.org_id == org_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        if actions:
            q = q.where(AuditLog.action.in_(actions))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def list_export_events(
        self,
        *,
        org_id: uuid.UUID,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 5000,
    ) -> list[AuditLog]:
        q = select(AuditLog).where(AuditLog.org_id == org_id).order_by(AuditLog.created_at.asc()).limit(limit)
        if since:
            q = q.where(AuditLog.created_at >= since)
        if until:
            q = q.where(AuditLog.created_at <= until)
        rows = await self.db.execute(q)
        return list(rows.scalars().all())
