from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest

from app.domain.services.payment_integration_service import PaymentIntegrationService


class _FakePaymentRepo:
    def __init__(self):
        self.connections_by_org: dict[uuid.UUID, SimpleNamespace] = {}
        self.connections_by_account: dict[str, SimpleNamespace] = {}
        self.webhook_events: dict[tuple[str, str], SimpleNamespace] = {}
        self.ledger_entries: dict[tuple[uuid.UUID, str, str, str], SimpleNamespace] = {}
        self.processor_totals_result = {
            "inflow": Decimal("0.00"),
            "outflow": Decimal("0.00"),
            "net": Decimal("0.00"),
            "entry_count": 0,
        }
        self.transaction_totals_result = {
            "revenue": Decimal("0.00"),
            "expense": Decimal("0.00"),
            "net": Decimal("0.00"),
            "entry_count": 0,
        }

    async def upsert_connection(
        self,
        *,
        org_id,
        connected_by_user_id,
        provider,
        provider_account_id,
        metadata_json,
        status,
    ):
        row = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            connected_by_user_id=connected_by_user_id,
            provider=provider,
            status=status,
            provider_account_id=provider_account_id,
            metadata_json=metadata_json or {},
            created_at="2026-03-01T00:00:00+00:00",
            updated_at="2026-03-01T00:00:00+00:00",
        )
        self.connections_by_org[org_id] = row
        if provider_account_id:
            self.connections_by_account[provider_account_id] = row
        return row

    async def get_connection_by_org_provider(self, *, org_id, provider):
        _ = provider
        return self.connections_by_org.get(org_id)

    async def get_connection_by_provider_account(self, *, provider, provider_account_id):
        _ = provider
        return self.connections_by_account.get(provider_account_id)

    async def get_webhook_event(self, *, provider, provider_event_id):
        return self.webhook_events.get((provider, provider_event_id))

    async def create_webhook_event(self, *, org_id, connection_id, provider, provider_event_id, event_type, payload):
        row = SimpleNamespace(
            id=uuid.uuid4(),
            org_id=org_id,
            connection_id=connection_id,
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            payload=payload,
            status="RECEIVED",
            error_message=None,
        )
        self.webhook_events[(provider, provider_event_id)] = row
        return row

    async def mark_webhook_event_status(self, row, *, status, error_message=None):
        row.status = status
        row.error_message = error_message
        return row

    async def upsert_ledger_entry(self, **kwargs):
        key = (
            kwargs["org_id"],
            kwargs["provider"],
            kwargs["external_event_id"],
            kwargs["entry_type"],
        )
        row = self.ledger_entries.get(key)
        if row is None:
            row = SimpleNamespace(id=uuid.uuid4(), **kwargs)
            self.ledger_entries[key] = row
        else:
            for k, v in kwargs.items():
                setattr(row, k, v)
        return row

    async def processor_totals(self, *, org_id, provider, date_from, date_to):
        _ = (org_id, provider, date_from, date_to)
        return self.processor_totals_result

    async def transaction_totals(self, *, org_id, date_from, date_to):
        _ = (org_id, date_from, date_to)
        return self.transaction_totals_result


class _FakeAuditRepo:
    def __init__(self):
        self.events = []

    async def log(self, **kwargs):
        self.events.append(kwargs)


def _service(repo: _FakePaymentRepo, audit: _FakeAuditRepo) -> PaymentIntegrationService:
    settings = SimpleNamespace(
        stripe_secret_key="sk_test_123",
        stripe_webhook_secret="whsec_test_123",
    )
    return PaymentIntegrationService(repo, audit, settings=settings)


@pytest.mark.asyncio
async def test_ingest_duplicate_event_returns_duplicate(monkeypatch):
    repo = _FakePaymentRepo()
    audit = _FakeAuditRepo()
    org_id = uuid.uuid4()
    repo.webhook_events[("STRIPE", "evt_duplicate")] = SimpleNamespace(
        id=uuid.uuid4(),
        org_id=org_id,
        status="PROCESSED",
    )
    svc = _service(repo, audit)

    monkeypatch.setattr(
        "app.domain.services.payment_integration_service.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: {
            "id": "evt_duplicate",
            "type": "charge.succeeded",
            "created": 1711300000,
            "data": {"object": {"amount": 1200, "currency": "usd", "metadata": {"org_id": str(org_id)}}},
        },
    )

    out = await svc.ingest_stripe_webhook(payload=b"{}", signature_header="sig")
    assert out.status == "DUPLICATE"
    assert out.event_id == "evt_duplicate"
    assert len(repo.ledger_entries) == 0


@pytest.mark.asyncio
async def test_ingest_charge_succeeded_records_ledger(monkeypatch):
    repo = _FakePaymentRepo()
    audit = _FakeAuditRepo()
    svc = _service(repo, audit)
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    await repo.upsert_connection(
        org_id=org_id,
        connected_by_user_id=actor_id,
        provider="STRIPE",
        provider_account_id=None,
        metadata_json={},
        status="ACTIVE",
    )

    monkeypatch.setattr(
        "app.domain.services.payment_integration_service.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: {
            "id": "evt_charge_1",
            "type": "charge.succeeded",
            "created": 1711300000,
            "data": {
                "object": {
                    "id": "ch_1",
                    "amount": 2450,
                    "currency": "usd",
                    "description": "Test payment",
                    "metadata": {"org_id": str(org_id)},
                }
            },
        },
    )

    out = await svc.ingest_stripe_webhook(payload=b"{}", signature_header="sig")
    assert out.status == "PROCESSED"
    assert len(repo.ledger_entries) == 1
    only = next(iter(repo.ledger_entries.values()))
    assert only.direction == "INFLOW"
    assert only.amount == Decimal("24.50")
    webhook = repo.webhook_events[("STRIPE", "evt_charge_1")]
    assert webhook.status == "PROCESSED"


@pytest.mark.asyncio
async def test_ingest_unsupported_event_skips(monkeypatch):
    repo = _FakePaymentRepo()
    audit = _FakeAuditRepo()
    svc = _service(repo, audit)
    org_id = uuid.uuid4()

    monkeypatch.setattr(
        "app.domain.services.payment_integration_service.stripe.Webhook.construct_event",
        lambda payload, sig_header, secret: {
            "id": "evt_other_1",
            "type": "customer.created",
            "created": 1711300000,
            "data": {"object": {"id": "cus_1", "metadata": {"org_id": str(org_id)}}},
        },
    )

    out = await svc.ingest_stripe_webhook(payload=b"{}", signature_header="sig")
    assert out.status == "SKIPPED"
    assert len(repo.ledger_entries) == 0
    webhook = repo.webhook_events[("STRIPE", "evt_other_1")]
    assert webhook.status == "SKIPPED"


@pytest.mark.asyncio
async def test_reconcile_computes_delta():
    repo = _FakePaymentRepo()
    repo.processor_totals_result = {
        "inflow": Decimal("1200.00"),
        "outflow": Decimal("200.00"),
        "net": Decimal("1000.00"),
        "entry_count": 5,
    }
    repo.transaction_totals_result = {
        "revenue": Decimal("1500.00"),
        "expense": Decimal("300.00"),
        "net": Decimal("1200.00"),
        "entry_count": 12,
    }
    svc = _service(repo, _FakeAuditRepo())
    org_id = uuid.uuid4()

    out = await svc.reconcile(
        org_id=org_id,
        provider="stripe",
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
    )
    assert out["provider"] == "STRIPE"
    assert out["delta"]["net"] == Decimal("200.00")
    assert out["delta"]["absolute"] == Decimal("200.00")
