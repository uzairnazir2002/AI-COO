from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.services.alerts_service import AlertsService


class _FakeRepo:
    async def save(self, _alert):
        return None


@pytest.mark.asyncio
async def test_assign_sets_assignment_and_clears_acknowledged_at():
    alert = SimpleNamespace(
        assigned_to_user_id=None,
        assigned_by_user_id=None,
        assigned_at=None,
        acknowledged_at=datetime.now(timezone.utc),
    )
    assignee = uuid4()
    actor = uuid4()

    await AlertsService(None, _FakeRepo()).assign(alert=alert, assignee_user_id=assignee, actor_user_id=actor)  # type: ignore[arg-type]

    assert alert.assigned_to_user_id == assignee
    assert alert.assigned_by_user_id == actor
    assert alert.assigned_at is not None
    assert alert.acknowledged_at is None


@pytest.mark.asyncio
async def test_acknowledge_sets_timestamp():
    alert = SimpleNamespace(acknowledged_at=None)

    await AlertsService(None, _FakeRepo()).acknowledge(alert=alert)  # type: ignore[arg-type]

    assert alert.acknowledged_at is not None
