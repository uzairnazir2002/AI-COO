from importlib import reload
from types import SimpleNamespace
import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeService:
    def __init__(self, *_args, **_kwargs):
        self.repo = SimpleNamespace(get_connection=self._get_connection)

    async def create_link_token(self, *, org_id, actor_user_id):
        _ = (org_id, actor_user_id)
        return {"link_token": "stub-token", "expiration": "2026-03-30T00:00:00+00:00"}

    async def exchange_public_token(self, *, org_id, actor_user_id, public_token, institution_name_override):
        _ = (org_id, actor_user_id, public_token, institution_name_override)
        conn_id = uuid.uuid4()
        connection = SimpleNamespace(
            id=conn_id,
            org_id=org_id,
            provider="PLAID",
            status="ACTIVE",
            institution_id="ins_123",
            institution_name="Demo Bank",
            connected_by_user_id=actor_user_id,
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
            revoked_at=None,
        )
        account = SimpleNamespace(
            id=uuid.uuid4(),
            external_account_id="acct_1",
            name="Checking",
            mask="1234",
            account_type="depository",
            account_subtype="checking",
            currency_code="USD",
            is_active=True,
        )
        return connection, [account]

    async def list_connections(self, org_id):
        connection = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            provider="PLAID",
            status="ACTIVE",
            institution_id="ins_123",
            institution_name="Demo Bank",
            connected_by_user_id=uuid.uuid4(),
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
            revoked_at=None,
        )
        return [connection]

    async def list_accounts(self, org_id, connection_id):
        _ = (org_id, connection_id)
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                external_account_id="acct_1",
                name="Checking",
                mask="1234",
                account_type="depository",
                account_subtype="checking",
                currency_code="USD",
                is_active=True,
            )
        ]

    async def revoke_connection(self, *, org_id, actor_user_id, connection_id):
        _ = (org_id, actor_user_id, connection_id)
        return None

    async def _get_connection(self, connection_id, org_id):
        _ = org_id
        return SimpleNamespace(id=connection_id)


class _FakePaymentService:
    def __init__(self, *_args, **_kwargs):
        pass

    async def list_connections(self, *, org_id, provider):
        _ = provider
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                org_id=org_id,
                provider="STRIPE",
                status="ACTIVE",
                provider_account_id="acct_list_1",
                connected_by_user_id=uuid.uuid4(),
                created_at="2026-03-25T00:00:00+00:00",
                updated_at="2026-03-25T00:00:00+00:00",
                metadata_json={"account_label": "Primary"},
            )
        ]

    async def connect_stripe(self, *, org_id, actor_user_id, provider_account_id, account_label):
        _ = (actor_user_id,)
        return SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            provider="STRIPE",
            status="ACTIVE",
            provider_account_id=provider_account_id,
            connected_by_user_id=actor_user_id,
            created_at="2026-03-25T00:00:00+00:00",
            updated_at="2026-03-25T00:00:00+00:00",
            metadata_json={"account_label": account_label} if account_label else {},
        )

    async def reconcile(self, *, org_id, provider, date_from, date_to):
        return {
            "org_id": org_id,
            "provider": provider.upper(),
            "date_from": date_from,
            "date_to": date_to,
            "processor": {
                "inflow": Decimal("1200.00"),
                "outflow": Decimal("100.00"),
                "net": Decimal("1100.00"),
                "entry_count": 3,
            },
            "transactions": {
                "revenue": Decimal("1250.00"),
                "expense": Decimal("180.00"),
                "net": Decimal("1070.00"),
                "entry_count": 5,
            },
            "delta": {
                "net": Decimal("-30.00"),
                "absolute": Decimal("30.00"),
            },
        }


class _FakeJobRepo:
    def __init__(self, _db):
        pass

    async def by_dedupe_key(self, _dedupe_key, _org_id=None):
        return None

    async def upsert_pending(self, **_kwargs):
        return None


class _FakeBankRepo:
    def __init__(self, _db):
        pass

    async def get_connection(self, connection_id, org_id):
        _ = org_id
        return SimpleNamespace(id=connection_id)


@pytest.fixture
def integrations_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    import app.api.v1.integrations as integrations

    return reload(integrations)


def _app_with_overrides(integrations_module, monkeypatch):
    app = FastAPI()
    app.include_router(integrations_module.router, prefix="/api/v1/integrations")

    class _FakeDb:
        def add(self, _obj):
            return None

        async def flush(self):
            return None

        async def commit(self):
            return None

    async def fake_user():
        return SimpleNamespace(id=uuid.uuid4(), email="owner@example.com")

    async def fake_db():
        yield _FakeDb()

    async def fake_ctx(org_id=None, user=None, db=None):
        _ = (org_id, user, db)
        return SimpleNamespace(org_id=org_id, role="OWNER")

    app.dependency_overrides[integrations_module.get_current_user] = fake_user
    app.dependency_overrides[integrations_module.get_db] = fake_db
    from app.api import deps as shared_deps

    app.dependency_overrides[shared_deps.get_org_context] = fake_ctx
    monkeypatch.setattr(integrations_module, "get_org_context", fake_ctx)
    monkeypatch.setattr(integrations_module, "BankIntegrationService", _FakeService)
    monkeypatch.setattr(integrations_module, "PaymentIntegrationService", _FakePaymentService)
    monkeypatch.setattr(integrations_module, "BankRepo", _FakeBankRepo)
    monkeypatch.setattr(integrations_module, "JobRepo", _FakeJobRepo)
    monkeypatch.setattr(
        integrations_module,
        "sync_bank_connection",
        SimpleNamespace(apply_async=lambda args: SimpleNamespace(id="bank-sync-task-1")),
    )
    return app


def test_link_token_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.post("/api/v1/integrations/banks/plaid/link-token", json={"org_id": str(org_id)})
    assert res.status_code == 200, res.text
    assert res.json()["link_token"] == "stub-token"


def test_exchange_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.post(
        "/api/v1/integrations/banks/plaid/exchange",
        json={"org_id": str(org_id), "public_token": "public-test-token"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["connection"]["provider"] == "PLAID"
    assert len(body["connection"]["accounts"]) == 1


def test_sync_enqueue_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    res = client.post(f"/api/v1/integrations/banks/{connection_id}/sync?org_id={org_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["job_id"] == "bank-sync-task-1"
    assert body["status"] == "PENDING"


def test_stripe_connect_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.post(
        "/api/v1/integrations/payments/stripe/connect",
        json={
            "org_id": str(org_id),
            "provider_account_id": "acct_123",
            "account_label": "Main Stripe",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["connection"]["provider"] == "STRIPE"
    assert body["connection"]["provider_account_id"] == "acct_123"
    assert body["connection"]["metadata_json"]["account_label"] == "Main Stripe"


def test_list_payment_connections_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.get(f"/api/v1/integrations/payments/connections?org_id={org_id}&provider=STRIPE")
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 1
    assert body[0]["provider"] == "STRIPE"
    assert body[0]["provider_account_id"] == "acct_list_1"


def test_payment_reconciliation_endpoint(monkeypatch, integrations_module):
    app = _app_with_overrides(integrations_module, monkeypatch)
    client = TestClient(app)
    org_id = uuid.uuid4()
    res = client.get(
        f"/api/v1/integrations/payments/reconciliation?org_id={org_id}&provider=STRIPE&date_from={date(2026, 3, 1)}&date_to={date(2026, 3, 31)}"
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["provider"] == "STRIPE"
    assert body["processor"]["net"] == "1100.00"
    assert body["transactions"]["net"] == "1070.00"
    assert body["delta"]["absolute"] == "30.00"
