from types import SimpleNamespace

import pytest


class RetryRaised(Exception):
    pass


class FakeTask:
    def __init__(self, retries: int):
        self.request = SimpleNamespace(retries=retries, id="task-1", headers={"x-request-id": "req-1"})

    def retry(self, exc: Exception, countdown: int):
        raise RetryRaised(f"retry countdown={countdown} exc={exc}")


@pytest.fixture
def tracking_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from importlib import reload
    import app.jobs.task_tracking as task_tracking

    return reload(task_tracking)


def test_run_tracked_task_success(monkeypatch, tracking_module):
    calls: list[str] = []
    captured: dict[str, str | None] = {}

    async def fake_mark_running(*, task_id, request_id, **_kwargs):
        captured["task_id"] = task_id
        captured["request_id"] = request_id
        calls.append("running")
        return "task-1"

    async def fake_mark_succeeded(task_id, result):
        calls.append(f"succeeded:{task_id}:{result['rows']}")

    async def runner():
        return 9

    monkeypatch.setattr(tracking_module, "mark_running", fake_mark_running)
    monkeypatch.setattr(tracking_module, "mark_succeeded", fake_mark_succeeded)

    result = tracking_module.run_tracked_task(
        FakeTask(retries=0),
        org_id="00000000-0000-0000-0000-000000000001",
        task_name="recalc_forecasts",
        dedupe_key="forecast:org",
        payload={"org_id": "org"},
        correlation_id="corr-1",
        max_retries=3,
        runner=runner,
        result_payload_builder=lambda v: {"rows": v},
    )

    assert result == 9
    assert calls == ["running", "succeeded:task-1:9"]
    assert captured == {"task_id": "task-1", "request_id": "req-1"}


def test_run_tracked_task_retrying(monkeypatch, tracking_module):
    calls: list[str] = []

    async def fake_mark_running(*args, **kwargs):
        calls.append("running")
        return "task-1"

    async def fake_mark_retrying(task_id, retry_count, error):
        calls.append(f"retrying:{task_id}:{retry_count}:{error}")

    async def runner():
        raise RuntimeError("boom")

    monkeypatch.setattr(tracking_module, "mark_running", fake_mark_running)
    monkeypatch.setattr(tracking_module, "mark_retrying", fake_mark_retrying)

    with pytest.raises(RetryRaised):
        tracking_module.run_tracked_task(
            FakeTask(retries=0),
            org_id="00000000-0000-0000-0000-000000000001",
            task_name="recalc_alerts",
            dedupe_key="alerts:org",
            payload={"org_id": "org"},
            correlation_id=None,
            max_retries=3,
            runner=runner,
            result_payload_builder=lambda v: {"value": v},
        )

    assert calls[0] == "running"
    assert calls[1].startswith("retrying:task-1:1:")


def test_run_tracked_task_failed_after_max_retries(monkeypatch, tracking_module):
    calls: list[str] = []

    async def fake_mark_running(*args, **kwargs):
        calls.append("running")
        return "task-1"

    async def fake_mark_failed(task_id, retry_count, error):
        calls.append(f"failed:{task_id}:{retry_count}:{error}")

    async def runner():
        raise ValueError("fatal")

    monkeypatch.setattr(tracking_module, "mark_running", fake_mark_running)
    monkeypatch.setattr(tracking_module, "mark_failed", fake_mark_failed)

    with pytest.raises(ValueError):
        tracking_module.run_tracked_task(
            FakeTask(retries=3),
            org_id="00000000-0000-0000-0000-000000000001",
            task_name="generate_weekly_report",
            dedupe_key="report:org:week",
            payload={"org_id": "org", "week_start": "2026-03-02"},
            correlation_id="corr-2",
            max_retries=3,
            runner=runner,
            result_payload_builder=lambda v: {"value": v},
        )

    assert calls[0] == "running"
    assert calls[1].startswith("failed:task-1:3:")
