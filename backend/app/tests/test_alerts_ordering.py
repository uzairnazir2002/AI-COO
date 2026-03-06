from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import uuid

import pytest

from app.domain.services.alerts_service import AlertsService


class _FakeRepo:
    def __init__(self, rows):
        self.rows = rows

    async def list_alerts(self, _org_id, _status):
        return self.rows


@pytest.mark.asyncio
async def test_alerts_are_ranked_by_severity_then_impact_then_recency():
    now = datetime.now(timezone.utc)
    low_high_impact = SimpleNamespace(
        severity="LOW",
        meta={"impact": "900.00"},
        created_at=now - timedelta(minutes=1),
    )
    medium_small_impact = SimpleNamespace(
        severity="MEDIUM",
        meta={"impact": "10.00"},
        created_at=now,
    )
    high_small_impact = SimpleNamespace(
        severity="HIGH",
        meta={"impact": "1.00"},
        created_at=now - timedelta(minutes=2),
    )
    high_large_impact = SimpleNamespace(
        severity="HIGH",
        meta={"impact": "500.00"},
        created_at=now - timedelta(minutes=3),
    )

    svc = AlertsService(None, _FakeRepo([low_high_impact, medium_small_impact, high_small_impact, high_large_impact]))  # type: ignore[arg-type]
    out = await svc.list_alerts(org_id=uuid.uuid4(), status="OPEN")

    assert out[0] is high_large_impact
    assert out[1] is high_small_impact
    assert out[2] is medium_small_impact
    assert out[3] is low_high_impact
