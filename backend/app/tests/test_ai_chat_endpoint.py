from datetime import datetime, timezone
from importlib import reload
from types import SimpleNamespace
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeDb:
    async def commit(self):
        return None


class _FakeUsageService:
    def __init__(self, _repo):
        pass

    async def consume(self, *_args, **_kwargs):
        return None


class _FakeAuditRepo:
    def __init__(self, _db):
        pass

    async def log(self, *_args, **_kwargs):
        return None


class _FakeAIChatService:
    created_session = None
    listed_sessions = []
    detail_session = None
    detail_messages = []
    chat_message = None
    raise_not_found_on_detail = False
    raise_not_found_on_chat = False

    def __init__(self, *_args, **_kwargs):
        pass

    async def create_session(self, **_kwargs):
        assert type(self).created_session is not None
        return type(self).created_session

    async def list_sessions(self, **_kwargs):
        return type(self).listed_sessions

    async def get_session_with_messages(self, **_kwargs):
        if type(self).raise_not_found_on_detail:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("AI chat session not found")
        assert type(self).detail_session is not None
        return type(self).detail_session, type(self).detail_messages

    async def chat(self, **_kwargs):
        if type(self).raise_not_found_on_chat:
            from app.domain.services.errors import NotFoundError

            raise NotFoundError("AI chat session not found")
        assert type(self).chat_message is not None
        return type(self).chat_message


@pytest.fixture
def ai_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.ai as ai

    _FakeAIChatService.created_session = None
    _FakeAIChatService.listed_sessions = []
    _FakeAIChatService.detail_session = None
    _FakeAIChatService.detail_messages = []
    _FakeAIChatService.chat_message = None
    _FakeAIChatService.raise_not_found_on_detail = False
    _FakeAIChatService.raise_not_found_on_chat = False

    return reload(ai)


def _app(monkeypatch, module):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1/ai")
    user = SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_user():
        return user

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        _ = (user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[module.get_current_user] = fake_user
    app.dependency_overrides[module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(module, "get_org_context", fake_ctx)
    monkeypatch.setattr(module, "AIChatService", _FakeAIChatService)
    monkeypatch.setattr(module, "UsageService", _FakeUsageService)
    monkeypatch.setattr(module, "AuditRepo", _FakeAuditRepo)
    monkeypatch.setattr(module, "AIChatRepo", lambda _db: object())
    monkeypatch.setattr(module, "AnalyticsRepo", lambda _db: object())
    monkeypatch.setattr(module, "AlertRepo", lambda _db: object())
    monkeypatch.setattr(module, "PlanRepo", lambda _db: object())
    return app


def test_ai_chat_create_session(ai_module, monkeypatch):
    org_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeAIChatService.created_session = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        created_by_user_id=uuid.uuid4(),
        title="Ops chat",
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )
    app = _app(monkeypatch, ai_module)
    client = TestClient(app)

    res = client.post("/api/v1/ai/chat/sessions", json={"org_id": str(org_id), "title": "Ops chat"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["org_id"] == str(org_id)
    assert body["title"] == "Ops chat"


def test_ai_chat_list_sessions(ai_module, monkeypatch):
    org_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeAIChatService.listed_sessions = [
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            title="Ops chat A",
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            created_by_user_id=uuid.uuid4(),
            title="Ops chat B",
            last_activity_at=now,
            created_at=now,
            updated_at=now,
        ),
    ]
    app = _app(monkeypatch, ai_module)
    client = TestClient(app)

    res = client.get(f"/api/v1/ai/chat/sessions?org_id={org_id}&mine_only=false&limit=20")
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert body[0]["org_id"] == str(org_id)


def test_ai_chat_get_session(ai_module, monkeypatch):
    org_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeAIChatService.raise_not_found_on_detail = False
    _FakeAIChatService.detail_session = SimpleNamespace(
        id=session_id,
        org_id=org_id,
        created_by_user_id=uuid.uuid4(),
        title="Ops chat",
        last_activity_at=now,
        created_at=now,
        updated_at=now,
    )
    _FakeAIChatService.detail_messages = [
        SimpleNamespace(
            id=uuid.uuid4(),
            session_id=session_id,
            org_id=org_id,
            created_by_user_id=None,
            role="ASSISTANT",
            content="Grounded answer",
            fallback_used=False,
            grounding_violations=[],
            created_at=now,
        )
    ]
    app = _app(monkeypatch, ai_module)
    client = TestClient(app)

    res = client.get(f"/api/v1/ai/chat/sessions/{session_id}?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["session"]["id"] == str(session_id)
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "ASSISTANT"


def test_ai_chat_get_session_not_found(ai_module, monkeypatch):
    org_id = uuid.uuid4()
    _FakeAIChatService.raise_not_found_on_detail = True
    app = _app(monkeypatch, ai_module)
    client = TestClient(app)

    res = client.get(f"/api/v1/ai/chat/sessions/{uuid.uuid4()}?org_id={org_id}")
    assert res.status_code == 404


def test_ai_chat_send_message(ai_module, monkeypatch):
    org_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    _FakeAIChatService.raise_not_found_on_chat = False
    _FakeAIChatService.chat_message = SimpleNamespace(
        id=uuid.uuid4(),
        session_id=session_id,
        org_id=org_id,
        created_by_user_id=None,
        role="ASSISTANT",
        content="Question: \"How is cash?\"",
        fallback_used=False,
        grounding_violations=[],
        created_at=now,
    )
    app = _app(monkeypatch, ai_module)
    client = TestClient(app)

    res = client.post(
        "/api/v1/ai/chat",
        json={
            "org_id": str(org_id),
            "session_id": str(session_id),
            "message": "How is cash?",
            "from": "2026-03-01",
            "to": "2026-03-26",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["session_id"] == str(session_id)
    assert body["message"]["role"] == "ASSISTANT"
