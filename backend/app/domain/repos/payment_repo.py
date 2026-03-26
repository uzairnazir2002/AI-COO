from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.payment_ledger_entry import PaymentLedgerEntry
from app.domain.models.payment_processor_connection import PaymentProcessorConnection
from app.domain.models.payment_webhook_event import PaymentWebhookEvent
from app.domain.models.transaction import Transaction


class PaymentRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_connection_by_org_provider(
        self, *, org_id: uuid.UUID, provider: str = "STRIPE"
    ) -> PaymentProcessorConnection | None:
        q = await self.db.execute(
            select(PaymentProcessorConnection).where(
                PaymentProcessorConnection.org_id == org_id,
                PaymentProcessorConnection.provider == provider,
            )
        )
        return q.scalar_one_or_none()

    async def list_connections(
        self, *, org_id: uuid.UUID, provider: str | None = None
    ) -> list[PaymentProcessorConnection]:
        stmt = select(PaymentProcessorConnection).where(PaymentProcessorConnection.org_id == org_id)
        if provider:
            stmt = stmt.where(PaymentProcessorConnection.provider == provider)
        stmt = stmt.order_by(PaymentProcessorConnection.created_at.desc())
        q = await self.db.execute(stmt)
        return list(q.scalars().all())

    async def get_connection_by_provider_account(
        self, *, provider: str, provider_account_id: str
    ) -> PaymentProcessorConnection | None:
        q = await self.db.execute(
            select(PaymentProcessorConnection).where(
                PaymentProcessorConnection.provider == provider,
                PaymentProcessorConnection.provider_account_id == provider_account_id,
            )
        )
        return q.scalar_one_or_none()

    async def upsert_connection(
        self,
        *,
        org_id: uuid.UUID,
        connected_by_user_id: uuid.UUID | None,
        provider: str,
        provider_account_id: str | None,
        metadata_json: dict | None = None,
        status: str = "ACTIVE",
    ) -> PaymentProcessorConnection:
        row = await self.get_connection_by_org_provider(org_id=org_id, provider=provider)
        if row is None:
            row = PaymentProcessorConnection(
                org_id=org_id,
                connected_by_user_id=connected_by_user_id,
                provider=provider,
                status=status,
                provider_account_id=provider_account_id,
                metadata_json=metadata_json or {},
            )
        else:
            row.connected_by_user_id = connected_by_user_id
            row.status = status
            row.provider_account_id = provider_account_id
            row.metadata_json = metadata_json or {}
            row.updated_at = datetime.now(tz=timezone.utc)
        self.db.add(row)
        await self.db.flush()
        return row

    async def get_webhook_event(
        self, *, provider: str, provider_event_id: str
    ) -> PaymentWebhookEvent | None:
        q = await self.db.execute(
            select(PaymentWebhookEvent).where(
                PaymentWebhookEvent.provider == provider,
                PaymentWebhookEvent.provider_event_id == provider_event_id,
            )
        )
        return q.scalar_one_or_none()

    async def create_webhook_event(
        self,
        *,
        org_id: uuid.UUID | None,
        connection_id: uuid.UUID | None,
        provider: str,
        provider_event_id: str,
        event_type: str,
        payload: dict,
    ) -> PaymentWebhookEvent:
        row = PaymentWebhookEvent(
            org_id=org_id,
            connection_id=connection_id,
            provider=provider,
            provider_event_id=provider_event_id,
            event_type=event_type,
            status="RECEIVED",
            payload=payload,
            error_message=None,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def mark_webhook_event_status(
        self,
        row: PaymentWebhookEvent,
        *,
        status: str,
        error_message: str | None = None,
    ) -> PaymentWebhookEvent:
        row.status = status
        row.error_message = error_message
        row.processed_at = datetime.now(tz=timezone.utc) if status in {"PROCESSED", "SKIPPED", "FAILED"} else None
        row.updated_at = datetime.now(tz=timezone.utc)
        self.db.add(row)
        await self.db.flush()
        return row

    async def upsert_ledger_entry(
        self,
        *,
        org_id: uuid.UUID,
        connection_id: uuid.UUID | None,
        webhook_event_id: uuid.UUID | None,
        provider: str,
        external_event_id: str,
        entry_type: str,
        direction: str,
        amount: Decimal,
        currency_code: str,
        occurred_at: datetime,
        description: str | None,
        metadata_json: dict | None = None,
    ) -> PaymentLedgerEntry:
        q = await self.db.execute(
            select(PaymentLedgerEntry).where(
                PaymentLedgerEntry.org_id == org_id,
                PaymentLedgerEntry.provider == provider,
                PaymentLedgerEntry.external_event_id == external_event_id,
                PaymentLedgerEntry.entry_type == entry_type,
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            row = PaymentLedgerEntry(
                org_id=org_id,
                connection_id=connection_id,
                webhook_event_id=webhook_event_id,
                provider=provider,
                external_event_id=external_event_id,
                entry_type=entry_type,
                direction=direction,
                amount=amount,
                currency_code=currency_code,
                occurred_at=occurred_at,
                description=description,
                metadata_json=metadata_json or {},
            )
        else:
            row.connection_id = connection_id
            row.webhook_event_id = webhook_event_id
            row.direction = direction
            row.amount = amount
            row.currency_code = currency_code
            row.occurred_at = occurred_at
            row.description = description
            row.metadata_json = metadata_json or {}
            row.updated_at = datetime.now(tz=timezone.utc)
        self.db.add(row)
        await self.db.flush()
        return row

    async def processor_totals(
        self, *, org_id: uuid.UUID, provider: str, date_from: date, date_to: date
    ) -> dict[str, Decimal | int]:
        start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        base = and_(
            PaymentLedgerEntry.org_id == org_id,
            PaymentLedgerEntry.provider == provider,
            PaymentLedgerEntry.occurred_at >= start_dt,
            PaymentLedgerEntry.occurred_at < end_dt,
        )
        inflow = await self.db.scalar(
            select(func.coalesce(func.sum(PaymentLedgerEntry.amount), 0)).where(
                base, PaymentLedgerEntry.direction == "INFLOW"
            )
        )
        outflow = await self.db.scalar(
            select(func.coalesce(func.sum(PaymentLedgerEntry.amount), 0)).where(
                base, PaymentLedgerEntry.direction == "OUTFLOW"
            )
        )
        count = await self.db.scalar(select(func.count()).select_from(PaymentLedgerEntry).where(base))
        inflow_d = Decimal(inflow or 0)
        outflow_d = Decimal(outflow or 0)
        return {
            "inflow": inflow_d,
            "outflow": outflow_d,
            "net": inflow_d - outflow_d,
            "entry_count": int(count or 0),
        }

    async def transaction_totals(self, *, org_id: uuid.UUID, date_from: date, date_to: date) -> dict[str, Decimal | int]:
        base = and_(
            Transaction.org_id == org_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        revenue = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(base, Transaction.type == "REVENUE")
        )
        expense = await self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(base, Transaction.type == "EXPENSE")
        )
        count = await self.db.scalar(select(func.count()).select_from(Transaction).where(base))
        revenue_d = Decimal(revenue or 0)
        expense_d = Decimal(expense or 0)
        return {
            "revenue": revenue_d,
            "expense": expense_d,
            "net": revenue_d - expense_d,
            "entry_count": int(count or 0),
        }
