from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.domain.models.ai_chat_message import AIChatMessage
from app.domain.models.ai_chat_session import AIChatSession
from app.domain.repos.ai_chat_repo import AIChatRepo
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.services.ai_service import AIService
from app.domain.services.analytics_service import AnalyticsService
from app.domain.services.errors import NotFoundError


class AIChatService:
    def __init__(
        self,
        chat_repo: AIChatRepo,
        analytics_repo: AnalyticsRepo,
        alerts_repo: AlertRepo,
        *,
        ai_service: AIService | None = None,
    ):
        self.chat_repo = chat_repo
        self.analytics_repo = analytics_repo
        self.alerts_repo = alerts_repo
        self.ai_service = ai_service or AIService()

    async def create_session(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        title: str | None = None,
    ) -> AIChatSession:
        normalized_title = (title or "").strip() or "New AI chat"
        return await self.chat_repo.create_session(
            AIChatSession(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                title=normalized_title,
                last_activity_at=datetime.now(tz=timezone.utc),
            )
        )

    async def list_sessions(
        self,
        *,
        org_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[AIChatSession]:
        return await self.chat_repo.list_sessions(
            org_id=org_id,
            created_by_user_id=created_by_user_id,
            limit=limit,
        )

    async def get_session_with_messages(
        self,
        *,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        limit: int = 100,
    ) -> tuple[AIChatSession, list[AIChatMessage]]:
        session = await self.chat_repo.get_session(org_id=org_id, session_id=session_id)
        if session is None:
            raise NotFoundError("AI chat session not found")
        messages = await self.chat_repo.list_messages(org_id=org_id, session_id=session_id, limit=limit)
        return session, messages

    async def chat(
        self,
        *,
        org_id: uuid.UUID,
        session_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        message: str,
        from_date,
        to_date,
    ) -> AIChatMessage:
        session = await self.chat_repo.get_session(org_id=org_id, session_id=session_id)
        if session is None:
            raise NotFoundError("AI chat session not found")

        now = datetime.now(tz=timezone.utc)
        user_msg = await self.chat_repo.create_message(
            AIChatMessage(
                session_id=session_id,
                org_id=org_id,
                created_by_user_id=actor_user_id,
                role="USER",
                content=message.strip(),
                fallback_used=False,
                grounding_violations=[],
            )
        )
        _ = user_msg

        summary = await AnalyticsService(self.analytics_repo).summary(org_id=org_id, from_date=from_date, to_date=to_date)
        alerts = await self.alerts_repo.list_alerts(org_id=org_id, status="OPEN")
        metrics = {
            "kpis": summary,
            "alerts": [{"title": a.title, "severity": a.severity} for a in alerts],
        }
        ai_reply = await self.ai_service.chat(user_message=message, metrics=metrics)
        assistant_msg = await self.chat_repo.create_message(
            AIChatMessage(
                session_id=session_id,
                org_id=org_id,
                created_by_user_id=None,
                role="ASSISTANT",
                content=ai_reply.answer,
                fallback_used=ai_reply.fallback_used,
                grounding_violations=ai_reply.grounding_violations,
            )
        )
        await self.chat_repo.touch_session(session=session, at=now)
        return assistant_msg
