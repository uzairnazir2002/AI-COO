from importlib import reload
from types import SimpleNamespace
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


class _FakePaymentService:
    should_fail = False

    def __init__(self, *_args, **_kwargs):
        pass

    async def ingest_stripe_webhook(self, *, payload, signature_header):
        _ = payload
        if self.should_fail:
            raise ValueError("bad stripe payload")
        assert signature_header == "sig_test"
        return SimpleNamespace(status="PROCESSED", event_id="evt_test_1", org_id=uuid.uuid4())


@pytest.fixture
def integrations_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.integrations as integrations

    return reload(integrations)


def _app(integrations_module, monkeypatch):
    app = FastAPI()
    app.include_router(integrations_module.router, prefix="/api/v1/integrations")

    async def fake_db():
        yield _FakeDb()

    app.dependency_overrides[integrations_module.get_db] = fake_db
    monkeypatch.setattr(integrations_module, "PaymentIntegrationService", _FakePaymentService)
    return app


def test_stripe_webhook_success(monkeypatch, integrations_module):
    _FakePaymentService.should_fail = False
    app = _app(integrations_module, monkeypatch)
    client = TestClient(app)
    res = client.post(
        "/api/v1/integrations/payments/stripe/webhook",
        content=b'{"id":"evt_test_1","type":"charge.succeeded","data":{"object":{}}}',
        headers={"Content-Type": "application/json", "Stripe-Signature": "sig_test"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["status"] == "PROCESSED"
    assert body["event_id"] == "evt_test_1"


def test_stripe_webhook_bad_payload_returns_400(monkeypatch, integrations_module):
    _FakePaymentService.should_fail = True
    app = _app(integrations_module, monkeypatch)
    client = TestClient(app)
    res = client.post(
        "/api/v1/integrations/payments/stripe/webhook",
        content=b'{"bad":"payload"}',
        headers={"Content-Type": "application/json", "Stripe-Signature": "sig_test"},
    )
    assert res.status_code == 400
    assert "bad stripe payload" in res.json()["detail"]
