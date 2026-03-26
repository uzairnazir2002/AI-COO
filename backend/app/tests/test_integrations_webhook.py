from importlib import reload
from types import SimpleNamespace
import hashlib
import hmac
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeDb:
    def add(self, _obj):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None


class _FakeBankRepo:
    def __init__(self, _db):
        pass

    async def list_active_connections_by_external_item(self, *, provider, external_item_id):
        _ = (provider, external_item_id)
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                org_id=uuid.uuid4(),
                connected_by_user_id=uuid.uuid4(),
            )
        ]


class _FakeJobRepo:
    def __init__(self, _db):
        self.pending = []

    async def by_dedupe_key(self, _dedupe_key, _org_id=None):
        return None

    async def upsert_pending(self, **kwargs):
        self.pending.append(kwargs)
        return None


@pytest.fixture
def integrations_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PLAID_WEBHOOK_SECRET", "plaid-secret-test")
    from app.core.config import get_settings
    get_settings.cache_clear()
    import app.api.v1.integrations as integrations

    return reload(integrations)


def _app(integrations_module, monkeypatch):
    app = FastAPI()
    app.include_router(integrations_module.router, prefix="/api/v1/integrations")

    async def fake_db():
        yield _FakeDb()

    app.dependency_overrides[integrations_module.get_db] = fake_db
    monkeypatch.setattr(integrations_module, "BankRepo", _FakeBankRepo)
    monkeypatch.setattr(integrations_module, "JobRepo", _FakeJobRepo)
    monkeypatch.setattr(
        integrations_module,
        "sync_bank_connection",
        SimpleNamespace(apply_async=lambda args: SimpleNamespace(id="webhook-sync-task")),
    )
    return app


def _sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_plaid_webhook_rejects_invalid_signature(monkeypatch, integrations_module):
    app = _app(integrations_module, monkeypatch)
    client = TestClient(app)
    payload = {"item_id": "item_123", "webhook_type": "TRANSACTIONS", "webhook_code": "SYNC_UPDATES_AVAILABLE"}
    res = client.post(
        "/api/v1/integrations/banks/plaid/webhook",
        json=payload,
        headers={"X-Plaid-Signature": "bad"},
    )
    assert res.status_code == 401


def test_plaid_webhook_enqueues_sync(monkeypatch, integrations_module):
    app = _app(integrations_module, monkeypatch)
    client = TestClient(app)
    body = b'{"item_id":"item_123","webhook_type":"TRANSACTIONS","webhook_code":"SYNC_UPDATES_AVAILABLE"}'
    signature = _sig("plaid-secret-test", body)
    res = client.post(
        "/api/v1/integrations/banks/plaid/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Plaid-Signature": signature},
    )
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True
    assert res.json()["enqueued"] == 1
