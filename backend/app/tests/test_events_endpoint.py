import uuid
from types import SimpleNamespace

import pytest


@pytest.fixture
def events_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.api.v1.events as events

    return reload(events)


@pytest.mark.asyncio
async def test_events_stream_returns_sse_response(events_module, monkeypatch):
    class _FakeAnalyticsService:
        def __init__(self, _repo):
            pass

        async def summary(self, _org_id, _from_date, _to_date):
            return {"cash_balance": "100.00"}

    class _FakeAlertRepo:
        def __init__(self, _db):
            pass

        async def list_alerts(self, _org_id, _status):
            return []

    async def fake_ctx(org_id: uuid.UUID, user=None, db=None):
        return SimpleNamespace(org_id=org_id, role="VIEWER")

    monkeypatch.setattr(events_module, "AnalyticsService", _FakeAnalyticsService)
    monkeypatch.setattr(events_module, "AlertRepo", _FakeAlertRepo)
    monkeypatch.setattr(events_module, "get_org_context", fake_ctx)

    resp = await events_module.stream_updates(
        org_id=uuid.uuid4(),
        interval_seconds=3,
        user=SimpleNamespace(id=uuid.uuid4(), email="viewer@example.com"),
        db=object(),
    )

    assert resp.media_type == "text/event-stream"
