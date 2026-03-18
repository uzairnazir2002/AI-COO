from types import SimpleNamespace
import uuid

import pytest


@pytest.fixture
def reports_tasks_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.tasks.reports as reports_tasks

    return reload(reports_tasks)


@pytest.mark.asyncio
async def test_generate_worker_runner_persists_report(monkeypatch, reports_tasks_module):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    report_id = uuid.uuid4()

    class _FakeDb:
        def __init__(self):
            self.committed = False

        async def commit(self):
            self.committed = True

    fake_db = _FakeDb()

    class _FakeSessionCtx:
        async def __aenter__(self):
            return fake_db

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeService:
        def __init__(self, _repo):
            self.calls = []

        async def generate(self, org_uuid, week_start, created_by):
            self.calls.append((org_uuid, week_start, created_by))
            return SimpleNamespace(id=report_id)

    fake_service = _FakeService(None)

    monkeypatch.setattr(reports_tasks_module, "SessionLocal", lambda: _FakeSessionCtx())
    monkeypatch.setattr(reports_tasks_module, "ReportRepo", lambda _db: object())
    monkeypatch.setattr(reports_tasks_module, "ReportService", lambda _repo: fake_service)

    out = await reports_tasks_module._generate(str(org_id), "2026-03-02", str(user_id), "corr-1")

    assert out == str(report_id)
    assert fake_db.committed is True
    assert len(fake_service.calls) == 1
