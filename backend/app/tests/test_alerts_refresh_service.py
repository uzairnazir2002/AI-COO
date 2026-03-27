from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.domain.services.alerts_refresh_service as alerts_refresh_module
from app.domain.services.alerts_refresh_service import AlertRefreshService


class _FakeJobRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.upsert_calls = []

    async def by_dedupe_key(self, dedupe_key, org_id):
        _ = (dedupe_key, org_id)
        return self.existing

    async def upsert_pending(self, **kwargs):
        self.upsert_calls.append(kwargs)


@pytest.mark.asyncio
async def test_enqueue_recalc_reuses_existing_active_job(monkeypatch):
    repo = _FakeJobRepo(existing=SimpleNamespace(task_id="existing-job", status="RUNNING"))
    called = False

    class _FakeTask:
        def apply_async(self, *args, **kwargs):
            nonlocal called
            called = True
            return SimpleNamespace(id="new-job")

    monkeypatch.setattr(alerts_refresh_module, "recalc_alerts", _FakeTask())
    out = await AlertRefreshService(repo).enqueue_recalc(org_id=uuid4())

    assert out.task_id == "existing-job"
    assert out.status == "RUNNING"
    assert out.enqueued is False
    assert called is False
    assert repo.upsert_calls == []


@pytest.mark.asyncio
async def test_enqueue_recalc_dispatches_and_tracks_job(monkeypatch):
    repo = _FakeJobRepo(existing=None)

    class _FakeTask:
        def apply_async(self, *args, **kwargs):
            return SimpleNamespace(id="new-alert-recalc-job")

    monkeypatch.setattr(alerts_refresh_module, "recalc_alerts", _FakeTask())
    org_id = uuid4()
    out = await AlertRefreshService(repo).enqueue_recalc(
        org_id=org_id,
        correlation_id="user-1",
        request_id="req-1",
        reason="test",
    )

    assert out.task_id == "new-alert-recalc-job"
    assert out.status == "PENDING"
    assert out.enqueued is True
    assert len(repo.upsert_calls) == 1
    upsert = repo.upsert_calls[0]
    assert upsert["task_name"] == "recalc_alerts"
    assert upsert["dedupe_key"] == f"alerts:{org_id}"
    assert upsert["payload"]["org_id"] == str(org_id)
    assert upsert["payload"]["reason"] == "test"

