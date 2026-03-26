import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.ai_chat_message import AIChatMessage
from app.domain.models.ai_chat_session import AIChatSession


class AIChatRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, session: AIChatSession) -> AIChatSession:
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, *, org_id: uuid.UUID, session_id: uuid.UUID) -> AIChatSession | None:
        row = await self.db.execute(
            select(AIChatSession).where(
                AIChatSession.id == session_id,
                AIChatSession.org_id == org_id,
            )
        )
        return row.scalar_one_or_none()

    async def list_sessions(self, *, org_id: uuid.UUID, created_by_user_id: uuid.UUID | None = None, limit: int = 50) -> list[AIChatSession]:
        stmt = select(AIChatSession).where(AIChatSession.org_id == org_id)
        if created_by_user_id is not None:
            stmt = stmt.where(AIChatSession.created_by_user_id == created_by_user_id)
        stmt = stmt.order_by(AIChatSession.last_activity_at.desc(), AIChatSession.created_at.desc()).limit(limit)
        rows = await self.db.execute(stmt)
        return list(rows.scalars().all())

    async def touch_session(self, *, session: AIChatSession, at: datetime) -> AIChatSession:
        session.last_activity_at = at
        await self.db.flush()
        return session

    async def create_message(self, message: AIChatMessage) -> AIChatMessage:
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_messages(self, *, org_id: uuid.UUID, session_id: uuid.UUID, limit: int = 100) -> list[AIChatMessage]:
        stmt = (
            select(AIChatMessage)
            .where(
                AIChatMessage.org_id == org_id,
                AIChatMessage.session_id == session_id,
            )
            .order_by(AIChatMessage.created_at.asc())
            .limit(limit)
        )
        rows = await self.db.execute(stmt)
        return list(rows.scalars().all())
