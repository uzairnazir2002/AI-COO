from types import SimpleNamespace

import pytest


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def ttl(self, key: str):
        return self.ttls.get(key, -1)

    async def delete(self, *keys: str):
        for key in keys:
            self.store.pop(key, None)
            self.ttls.pop(key, None)

    async def incr(self, key: str):
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    async def expire(self, key: str, seconds: int):
        self.ttls[key] = int(seconds)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = str(value)
        if ex is not None:
            self.ttls[key] = int(ex)


@pytest.mark.asyncio
async def test_record_login_failure_tracks_escalation_metrics(monkeypatch):
    from app.core import auth_lockout as module

    fake_redis = _FakeRedis()
    monkeypatch.setattr(module, "redis_client", fake_redis)
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            auth_lockout_window_minutes=15,
            auth_lockout_duration_minutes=30,
            auth_lockout_threshold=2,
        ),
    )

    first = await module.record_login_failure("owner@example.com", "127.0.0.1")
    second = await module.record_login_failure("owner@example.com", "127.0.0.1")
    third = await module.record_login_failure("owner@example.com", "127.0.0.1")
    fourth = await module.record_login_failure("owner@example.com", "127.0.0.1")

    assert first.escalation_level == 0
    assert second.escalation_level == 1
    assert second.escalated is True
    assert third.escalation_level == 1
    assert third.escalated is False
    assert fourth.escalation_level == 2
    assert fourth.escalated is True
    assert fourth.locked is True

    metrics = await module.lockout_metrics()
    assert metrics["failures_total"] == 4
    assert metrics["lockouts_total"] >= 1
    assert metrics["escalations_total"] == 2


@pytest.mark.asyncio
async def test_clear_login_failures_clears_escalation_key(monkeypatch):
    from app.core import auth_lockout as module

    fake_redis = _FakeRedis()
    monkeypatch.setattr(module, "redis_client", fake_redis)
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: SimpleNamespace(
            auth_lockout_window_minutes=15,
            auth_lockout_duration_minutes=30,
            auth_lockout_threshold=1,
        ),
    )

    await module.record_login_failure("owner@example.com", "127.0.0.1")
    status_before = await module.is_locked("owner@example.com", "127.0.0.1")
    assert status_before.escalation_level >= 1

    await module.clear_login_failures("owner@example.com", "127.0.0.1")
    status_after = await module.is_locked("owner@example.com", "127.0.0.1")
    assert status_after.locked is False
    assert status_after.escalation_level == 0
