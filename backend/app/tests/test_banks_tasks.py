from types import SimpleNamespace
import uuid

import pytest


@pytest.fixture
def banks_tasks_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.tasks.banks as banks_tasks

    return reload(banks_tasks)


@pytest.mark.asyncio
async def test_sync_all_active_enqueues_connections_with_actor(monkeypatch, banks_tasks_module):
    org_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    actor_user_id = uuid.uuid4()
    delayed = []

    class _Rows:
        def all(self):
            return [
                (connection_id, org_id, actor_user_id),
                (uuid.uuid4(), uuid.uuid4(), None),
            ]

    class _FakeDb:
        async def execute(self, _stmt):
            return _Rows()

    class _SessionCtx:
        async def __aenter__(self):
            return _FakeDb()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeScheduleRepo:
        def __init__(self, _db):
            pass

        async def get(self, _name):
            return None

    monkeypatch.setattr(banks_tasks_module, "SessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr(banks_tasks_module, "ScheduleRepo", _FakeScheduleRepo)
    monkeypatch.setattr(
        banks_tasks_module,
        "sync_bank_connection",
        SimpleNamespace(delay=lambda *args: delayed.append(args)),
    )

    out = await banks_tasks_module._sync_all_active()

    assert out["paused"] is False
    assert out["enqueued"] == 1
    assert out["skipped_without_actor"] == 1
    assert len(delayed) == 1
