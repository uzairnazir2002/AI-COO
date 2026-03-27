import uuid
from types import SimpleNamespace

import pytest

from app.domain.services.errors import ConflictError
from app.domain.services.idempotency_service import IdempotencyService
from app.utils.time import utc_now


class _FakeRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.upserts = []

    async def get_active(self, **_kwargs):
        return self.existing

    async def upsert_completed(self, **kwargs):
        self.upserts.append(kwargs)


@pytest.mark.asyncio
async def test_get_replay_returns_existing_response():
    existing = SimpleNamespace(
        request_hash="abc",
        status_code=200,
        response_json={"ok": True},
    )
    svc = IdempotencyService(_FakeRepo(existing=existing))
    out = await svc.get_replay(
        org_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        endpoint="POST /api/v1/reports/generate",
        idempotency_key="idem-1",
        request_hash="abc",
    )
    assert out is not None
    assert out.response_json["ok"] is True


@pytest.mark.asyncio
async def test_get_replay_rejects_mismatched_payload():
    existing = SimpleNamespace(
        request_hash="abc",
        status_code=200,
        response_json={"ok": True},
    )
    svc = IdempotencyService(_FakeRepo(existing=existing))
    with pytest.raises(ConflictError):
        await svc.get_replay(
            org_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            endpoint="POST /api/v1/reports/generate",
            idempotency_key="idem-1",
            request_hash="different",
        )


@pytest.mark.asyncio
async def test_store_response_noops_without_key():
    repo = _FakeRepo()
    svc = IdempotencyService(repo)
    await svc.store_response(
        org_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        endpoint="POST /api/v1/reports/generate",
        idempotency_key=None,
        request_hash="abc",
        status_code=200,
        response_json={"ok": True},
    )
    assert repo.upserts == []


@pytest.mark.asyncio
async def test_store_response_persists_with_ttl(monkeypatch):
    repo = _FakeRepo()
    svc = IdempotencyService(repo)
    before = utc_now()
    await svc.store_response(
        org_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        endpoint="POST /api/v1/transactions",
        idempotency_key="idem-2",
        request_hash="abc",
        status_code=200,
        response_json={"ok": True},
    )
    assert len(repo.upserts) == 1
    assert repo.upserts[0]["expires_at"] > before
