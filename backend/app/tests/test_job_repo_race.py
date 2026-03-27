from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.repos.job_repo import JobRepo


class _NestedTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeDb:
    def __init__(self, scalar_results):
        self._scalar_results = list(scalar_results)
        self.flush_calls = 0
        self.add_calls = 0

    async def scalar(self, _stmt):
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    def add(self, _obj):
        self.add_calls += 1

    def begin_nested(self):
        return _NestedTx()

    async def flush(self):
        self.flush_calls += 1
        if self.flush_calls == 1:
            raise IntegrityError("insert", {}, Exception("duplicate key value"))


@pytest.mark.asyncio
async def test_upsert_running_handles_concurrent_insert_race_without_task_id_drift():
    existing = SimpleNamespace(
        task_id="api-task-id",
        task_name="sync_bank_connection",
        job_name="sync_bank_connection",
        dedupe_key="bank-sync:org:conn",
        payload={"org_id": "org"},
        org_id=None,
        request_id=None,
        correlation_id=None,
        status="PENDING",
        last_error=None,
        traceback_summary=None,
        updated_at=None,
    )
    db = _FakeDb([None, existing])
    repo = JobRepo(db)  # type: ignore[arg-type]

    out = await repo.upsert_running(
        task_id="worker-random-id",
        task_name="sync_bank_connection",
        dedupe_key="bank-sync:org:conn",
        payload={"org_id": "org"},
        org_id=None,
        request_id="req-1",
        correlation_id="corr-1",
    )

    assert out is existing
    assert existing.task_id == "api-task-id"
    assert existing.status == "RUNNING"
    assert db.add_calls == 1
    assert db.flush_calls == 2


@pytest.mark.asyncio
async def test_upsert_pending_does_not_downgrade_running_row_after_race():
    existing = SimpleNamespace(
        task_id="api-task-id",
        task_name="sync_bank_connection",
        job_name="sync_bank_connection",
        dedupe_key="bank-sync:org:conn",
        payload={"org_id": "org"},
        org_id=None,
        request_id=None,
        correlation_id=None,
        status="RUNNING",
        progress=0,
        result=None,
        retry_count=0,
        last_retry_at=None,
        last_error=None,
        traceback_summary=None,
        updated_at=None,
    )
    db = _FakeDb([None, existing])
    repo = JobRepo(db)  # type: ignore[arg-type]

    out = await repo.upsert_pending(
        task_id="api-task-id",
        task_name="sync_bank_connection",
        dedupe_key="bank-sync:org:conn",
        payload={"org_id": "org"},
        org_id=None,
        request_id="req-1",
        correlation_id="corr-1",
    )

    assert out is existing
    assert existing.status == "RUNNING"
    assert db.add_calls == 1
    assert db.flush_calls == 1
