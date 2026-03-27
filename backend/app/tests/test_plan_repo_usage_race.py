from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.repos.plan_repo import PlanRepo


class _NestedTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDb:
    def __init__(self):
        self.flush_calls = 0
        self.add_calls = 0

    def begin_nested(self):
        return _NestedTx()

    def add(self, _obj):
        self.add_calls += 1

    async def flush(self):
        self.flush_calls += 1
        if self.flush_calls == 1:
            raise IntegrityError("insert", {}, Exception("duplicate key value"))


@pytest.mark.asyncio
async def test_ensure_usage_handles_concurrent_insert_race():
    db = _FakeDb()
    repo = PlanRepo(db)  # type: ignore[arg-type]
    existing = SimpleNamespace(soft_limit=100)

    state = {"calls": 0}

    async def fake_get_usage(_org_id, _metric, _period_start):
        state["calls"] += 1
        if state["calls"] == 1:
            return None
        return existing

    repo.get_usage = fake_get_usage  # type: ignore[method-assign]
    out = await repo.ensure_usage(
        org_id=SimpleNamespace(),
        metric="reports",
        period_start=SimpleNamespace(),
        soft_limit=200,
    )

    assert out is existing
    assert existing.soft_limit == 200
    assert db.add_calls == 1
    assert db.flush_calls == 2
