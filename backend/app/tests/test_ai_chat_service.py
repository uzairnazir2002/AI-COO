from datetime import date, datetime
import uuid

import pytest

from app.domain.models.ai_chat_message import AIChatMessage
from app.domain.models.ai_chat_session import AIChatSession
from app.domain.services.ai_chat_service import AIChatService
from app.domain.services.ai_service import AIChatGeneration
from app.domain.services.errors import NotFoundError


class _InMemoryChatRepo:
    def __init__(self):
        self.sessions: dict[uuid.UUID, AIChatSession] = {}
        self.messages: list[AIChatMessage] = []

    async def create_session(self, session: AIChatSession) -> AIChatSession:
        if session.id is None:
            session.id = uuid.uuid4()
        self.sessions[session.id] = session
        return session

    async def get_session(self, *, org_id: uuid.UUID, session_id: uuid.UUID) -> AIChatSession | None:
        session = self.sessions.get(session_id)
        if session is None or session.org_id != org_id:
            return None
        return session

    async def list_sessions(self, *, org_id: uuid.UUID, created_by_user_id: uuid.UUID | None = None, limit: int = 50):
        rows = [s for s in self.sessions.values() if s.org_id == org_id]
        if created_by_user_id is not None:
            rows = [s for s in rows if s.created_by_user_id == created_by_user_id]
        return rows[:limit]

    async def touch_session(self, *, session: AIChatSession, at: datetime) -> AIChatSession:
        session.last_activity_at = at
        session.updated_at = at
        return session

    async def create_message(self, message: AIChatMessage) -> AIChatMessage:
        if message.id is None:
            message.id = uuid.uuid4()
        self.messages.append(message)
        return message

    async def list_messages(self, *, org_id: uuid.UUID, session_id: uuid.UUID, limit: int = 100) -> list[AIChatMessage]:
        rows = [m for m in self.messages if m.org_id == org_id and m.session_id == session_id]
        return rows[:limit]


class _FakeAnalyticsRepo:
    def __init__(self):
        self.calls = 0

    async def summary_snapshot(self, org_id, month, *, location_id=None):
        _ = (org_id, month, location_id)
        self.calls += 1
        return {
            "revenue_mtd": 1000,
            "expense_mtd": 700,
            "starting_cash": 5000,
            "revenue_total": 1000,
            "expense_total": 700,
            "alerts_open": 1,
        }


class _FakeAlert:
    def __init__(self, title: str, severity: str):
        self.title = title
        self.severity = severity


class _FakeAlertsRepo:
    async def list_alerts(self, org_id, status):
        _ = (org_id, status)
        return [_FakeAlert("Runway low", "HIGH")]


class _FakeAIService:
    async def chat(self, user_message: str, metrics: dict) -> AIChatGeneration:
        assert "kpis" in metrics
        assert "alerts" in metrics
        return AIChatGeneration(
            answer=f"Question: \"{user_message}\"",
            fallback_used=False,
            grounding_violations=[],
        )


@pytest.mark.asyncio
async def test_ai_chat_service_roundtrip():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session_repo = _InMemoryChatRepo()
    analytics_repo = _FakeAnalyticsRepo()
    alerts_repo = _FakeAlertsRepo()
    service = AIChatService(
        session_repo,
        analytics_repo,
        alerts_repo,
        ai_service=_FakeAIService(),
    )

    session = await service.create_session(org_id=org_id, actor_user_id=user_id, title="Cash chat")
    assert session.title == "Cash chat"

    message = await service.chat(
        org_id=org_id,
        session_id=session.id,
        actor_user_id=user_id,
        message="How is cash this month?",
        from_date=date(2026, 3, 1),
        to_date=date(2026, 3, 26),
    )
    assert message.role == "ASSISTANT"
    assert message.fallback_used is False
    assert len(session_repo.messages) == 2
    assert session_repo.messages[0].role == "USER"
    assert session_repo.messages[1].role == "ASSISTANT"

    loaded_session, loaded_messages = await service.get_session_with_messages(org_id=org_id, session_id=session.id)
    assert loaded_session.id == session.id
    assert len(loaded_messages) == 2


@pytest.mark.asyncio
async def test_ai_chat_service_not_found():
    service = AIChatService(_InMemoryChatRepo(), _FakeAnalyticsRepo(), _FakeAlertsRepo(), ai_service=_FakeAIService())

    with pytest.raises(NotFoundError):
        await service.chat(
            org_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            actor_user_id=uuid.uuid4(),
            message="hello",
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 26),
        )


@pytest.mark.asyncio
async def test_ai_chat_service_list_sessions():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    service = AIChatService(_InMemoryChatRepo(), _FakeAnalyticsRepo(), _FakeAlertsRepo(), ai_service=_FakeAIService())

    mine = await service.create_session(org_id=org_id, actor_user_id=user_id, title="Mine")
    _ = mine
    await service.create_session(org_id=org_id, actor_user_id=other_user_id, title="Other")

    all_sessions = await service.list_sessions(org_id=org_id, limit=50)
    assert len(all_sessions) == 2

    my_sessions = await service.list_sessions(org_id=org_id, created_by_user_id=user_id, limit=50)
    assert len(my_sessions) == 1
    assert my_sessions[0].created_by_user_id == user_id
