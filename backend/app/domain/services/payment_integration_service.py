from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import stripe

from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.payment_repo import PaymentRepo


@dataclass(slots=True)
class StripeWebhookIngestResult:
    status: str
    event_id: str
    org_id: uuid.UUID | None
    message: str | None = None


class PaymentIntegrationService:
    def __init__(
        self,
        repo: PaymentRepo,
        audit_repo: AuditRepo,
        *,
        settings: Any | None = None,
        stripe_secret_key: str = "",
        stripe_webhook_secret: str = "",
    ):
        self.repo = repo
        self.audit_repo = audit_repo
        if settings is not None:
            self.stripe_secret_key = getattr(settings, "stripe_secret_key", "") or ""
            self.stripe_webhook_secret = getattr(settings, "stripe_webhook_secret", "") or ""
        else:
            self.stripe_secret_key = stripe_secret_key or ""
            self.stripe_webhook_secret = stripe_webhook_secret or ""

    async def connect_stripe(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        provider_account_id: str | None,
        account_label: str | None = None,
    ):
        metadata_json = {"account_label": account_label} if account_label else {}
        connection = await self.repo.upsert_connection(
            org_id=org_id,
            connected_by_user_id=actor_user_id,
            provider="STRIPE",
            provider_account_id=provider_account_id,
            metadata_json=metadata_json,
            status="ACTIVE",
        )
        await self.audit_repo.log(
            actor_user_id=actor_user_id,
            org_id=org_id,
            action="payment.stripe.connection.upsert",
            entity_type="payment_connection",
            entity_id=str(connection.id),
            metadata_json={
                "provider_account_id": provider_account_id,
                "account_label": account_label,
            },
        )
        return connection

    async def list_connections(self, *, org_id: uuid.UUID, provider: str = "STRIPE"):
        return await self.repo.list_connections(org_id=org_id, provider=provider)

    async def ingest_stripe_webhook(
        self,
        *,
        payload: bytes,
        signature_header: str | None,
    ) -> StripeWebhookIngestResult:
        event = self._construct_stripe_event(payload=payload, signature_header=signature_header)
        event_id = str(event.get("id") or "")
        if not event_id:
            raise ValueError("Invalid Stripe event payload: missing event id")
        existing = await self.repo.get_webhook_event(provider="STRIPE", provider_event_id=event_id)
        if existing:
            return StripeWebhookIngestResult(status="DUPLICATE", event_id=event_id, org_id=existing.org_id)

        event_type = str(event.get("type") or "unknown")
        obj = event.get("data", {}).get("object", {}) if isinstance(event.get("data"), dict) else {}
        org_id, connection_id = await self._resolve_org_and_connection(event=event, obj=obj)

        webhook_row = await self.repo.create_webhook_event(
            org_id=org_id,
            connection_id=connection_id,
            provider="STRIPE",
            provider_event_id=event_id,
            event_type=event_type,
            payload=event,
        )

        try:
            ledger_payload = self._build_ledger_payload(
                event=event,
                obj=obj,
                org_id=org_id,
                connection_id=connection_id,
                webhook_event_id=webhook_row.id,
            )
            if ledger_payload is None:
                await self.repo.mark_webhook_event_status(
                    webhook_row, status="SKIPPED", error_message="Event ignored or missing org context"
                )
                return StripeWebhookIngestResult(
                    status="SKIPPED",
                    event_id=event_id,
                    org_id=org_id,
                    message="Event ignored or missing org context",
                )

            ledger = await self.repo.upsert_ledger_entry(**ledger_payload)
            await self.repo.mark_webhook_event_status(webhook_row, status="PROCESSED", error_message=None)
            await self.audit_repo.log(
                actor_user_id=None,
                org_id=org_id,
                action="payment.stripe.webhook.processed",
                entity_type="payment_webhook_event",
                entity_id=str(webhook_row.id),
                metadata_json={
                    "provider_event_id": event_id,
                    "entry_type": ledger.entry_type,
                    "direction": ledger.direction,
                    "amount": str(ledger.amount),
                },
            )
            return StripeWebhookIngestResult(status="PROCESSED", event_id=event_id, org_id=org_id)
        except Exception as exc:
            await self.repo.mark_webhook_event_status(webhook_row, status="FAILED", error_message=str(exc))
            if org_id:
                await self.audit_repo.log(
                    actor_user_id=None,
                    org_id=org_id,
                    action="payment.stripe.webhook.failed",
                    entity_type="payment_webhook_event",
                    entity_id=str(webhook_row.id),
                    metadata_json={"provider_event_id": event_id, "error": str(exc)},
                )
            raise

    async def reconcile(
        self,
        *,
        org_id: uuid.UUID,
        provider: str,
        date_from: date,
        date_to: date,
    ) -> dict:
        provider_u = provider.upper()
        processor = await self.repo.processor_totals(
            org_id=org_id, provider=provider_u, date_from=date_from, date_to=date_to
        )
        transactions = await self.repo.transaction_totals(org_id=org_id, date_from=date_from, date_to=date_to)
        delta_net = transactions["net"] - processor["net"]
        return {
            "org_id": org_id,
            "provider": provider_u,
            "date_from": date_from,
            "date_to": date_to,
            "processor": processor,
            "transactions": transactions,
            "delta": {"net": delta_net, "absolute": abs(delta_net)},
        }

    def _normalize_event(self, event: Any) -> dict[str, Any]:
        if isinstance(event, dict):
            return event
        to_dict_recursive = getattr(event, "to_dict_recursive", None)
        if callable(to_dict_recursive):
            normalized = to_dict_recursive()
            if isinstance(normalized, dict):
                return normalized
        to_dict = getattr(event, "to_dict", None)
        if callable(to_dict):
            normalized = to_dict()
            if isinstance(normalized, dict):
                return normalized
        try:
            normalized = dict(event)
            if isinstance(normalized, dict):
                return normalized
        except Exception:
            pass
        raise ValueError("Invalid Stripe event payload: unable to normalize event")

    def _construct_stripe_event(self, *, payload: bytes, signature_header: str | None) -> dict[str, Any]:
        if self.stripe_webhook_secret:
            if not signature_header:
                raise ValueError("Missing Stripe signature header")
            try:
                event = stripe.Webhook.construct_event(
                    payload=payload,
                    sig_header=signature_header,
                    secret=self.stripe_webhook_secret,
                )
                return self._normalize_event(event)
            except Exception as exc:
                raise ValueError(f"Invalid Stripe webhook signature: {exc}") from exc
        try:
            parsed = json.loads(payload.decode("utf-8"))
            event = stripe.Event.construct_from(parsed, self.stripe_secret_key)
            return self._normalize_event(event)
        except Exception as exc:
            raise ValueError(f"Invalid Stripe webhook payload: {exc}") from exc

    async def _resolve_org_and_connection(
        self, *, event: dict, obj: dict
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        org_id = None
        metadata = obj.get("metadata") if isinstance(obj, dict) else None
        if isinstance(metadata, dict):
            org_id_raw = metadata.get("org_id")
            if org_id_raw:
                try:
                    org_id = uuid.UUID(str(org_id_raw))
                except ValueError:
                    org_id = None

        provider_account_id = event.get("account") or obj.get("account")
        connection = None
        if provider_account_id:
            connection = await self.repo.get_connection_by_provider_account(
                provider="STRIPE", provider_account_id=str(provider_account_id)
            )
        if connection is None and org_id is not None:
            connection = await self.repo.get_connection_by_org_provider(org_id=org_id, provider="STRIPE")
        if org_id is None and connection is not None:
            org_id = connection.org_id
        return org_id, connection.id if connection else None

    def _build_ledger_payload(
        self,
        *,
        event: dict,
        obj: dict,
        org_id: uuid.UUID | None,
        connection_id: uuid.UUID | None,
        webhook_event_id: uuid.UUID,
    ) -> dict | None:
        mapped = self._map_event_to_entry(event_type=str(event.get("type") or ""), obj=obj)
        if mapped is None or org_id is None:
            return None

        direction, amount_minor, entry_type = mapped
        amount = (Decimal(amount_minor) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        created_unix = event.get("created") or obj.get("created")
        if isinstance(created_unix, int):
            occurred_at = datetime.fromtimestamp(created_unix, tz=timezone.utc)
        else:
            occurred_at = datetime.now(tz=timezone.utc)
        currency_code = str(obj.get("currency") or "USD").upper()
        description = obj.get("description") or obj.get("statement_descriptor") or str(event.get("type") or "")
        return {
            "org_id": org_id,
            "connection_id": connection_id,
            "webhook_event_id": webhook_event_id,
            "provider": "STRIPE",
            "external_event_id": str(event.get("id") or ""),
            "entry_type": entry_type,
            "direction": direction,
            "amount": amount,
            "currency_code": currency_code,
            "occurred_at": occurred_at,
            "description": description,
            "metadata_json": {
                "object_id": obj.get("id"),
                "raw_type": event.get("type"),
            },
        }

    def _map_event_to_entry(self, *, event_type: str, obj: dict) -> tuple[str, int, str] | None:
        event_type = event_type.strip()
        amount_minor = None
        direction = None
        if event_type == "charge.succeeded":
            amount_minor = obj.get("amount_captured") or obj.get("amount")
            direction = "INFLOW"
        elif event_type in {"charge.refunded", "refund.created", "charge.dispute.created"}:
            amount_minor = obj.get("amount_refunded") or obj.get("amount")
            direction = "OUTFLOW"
        elif event_type in {"invoice.paid", "invoice.payment_succeeded"}:
            amount_minor = obj.get("amount_paid") or obj.get("amount_due")
            direction = "INFLOW"
        elif event_type == "payment_intent.succeeded":
            amount_minor = obj.get("amount_received") or obj.get("amount")
            direction = "INFLOW"
        if direction is None or amount_minor is None:
            return None
        try:
            parsed_amount = int(amount_minor)
        except (TypeError, ValueError):
            return None
        if parsed_amount < 0:
            parsed_amount = abs(parsed_amount)
        entry_type = event_type.upper().replace(".", "_")
        return direction, parsed_amount, entry_type
