import uuid
from datetime import date
from types import SimpleNamespace

import pytest

from app.domain.services.errors import LimitExceededError
from app.domain.services.usage_service import METRIC_AI_SUMMARIES, UsageService


class _FakeRepo:
    def __init__(self):
        self.plan = None
        self.usage = {}

    async def get_plan(self, org_id):
        return self.plan

    async def save_plan(self, plan):
        self.plan = plan
        return plan

    async def ensure_usage(self, org_id, metric, period_start, soft_limit):
        key = (org_id, metric, period_start)
        if key not in self.usage:
            self.usage[key] = SimpleNamespace(used_count=0, soft_limit=soft_limit)
        return self.usage[key]

    async def increment_usage(self, usage, delta):
        usage.used_count += delta
        return usage


@pytest.mark.asyncio
async def test_usage_limit_exceeded():
    org_id = uuid.uuid4()
    repo = _FakeRepo()
    svc = UsageService(repo)  # type: ignore[arg-type]

    await svc.consume(org_id, METRIC_AI_SUMMARIES, delta=500)
    with pytest.raises(LimitExceededError):
        await svc.consume(org_id, METRIC_AI_SUMMARIES, delta=1)


@pytest.mark.asyncio
async def test_usage_overview_returns_metrics():
    org_id = uuid.uuid4()
    repo = _FakeRepo()
    svc = UsageService(repo)  # type: ignore[arg-type]
    overview = await svc.get_usage_overview(org_id)
    assert overview["plan_code"] == "FREE"
    assert overview["period_start"] == date.today().replace(day=1)
    assert "transactions" in overview["metrics"]
