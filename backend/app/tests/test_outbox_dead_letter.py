from datetime import datetime, timezone
from types import SimpleNamespace

import pytest


class _FakeDb:
    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_outbox_terminal_failure_records_dead_letter(monkeypatch):
    from app.domain.repos import outbox_repo as module

    captured: dict = {}

    class _FakeDeadLetterRepo:
        def __init__(self, _db):
            pass

        async def record_failure(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id="dlq-1")

    monkeypatch.setattr(module, "DeadLetterRepo", _FakeDeadLetterRepo)
    repo = module.OutboxRepo(_FakeDb())
    event = SimpleNamespace(
        id="e1",
        org_id="org-1",
        event_type="email.send",
        payload={"to": "owner@example.com"},
        attempts=4,
        max_attempts=5,
        status="RETRYING",
        last_error=None,
        available_at=datetime.now(timezone.utc),
    )

    await repo.mark_retry_or_failed(event, "smtp timeout")

    assert event.status == "FAILED"
    assert captured["source_type"] == "OUTBOX"
    assert captured["source_name"] == "email.send"
    assert captured["attempts"] == 5
