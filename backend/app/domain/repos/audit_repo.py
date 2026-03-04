import uuid

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
