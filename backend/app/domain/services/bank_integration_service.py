from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import get_settings
from app.domain.models.bank_account import BankAccount
from app.domain.models.bank_connection import BankConnection
from app.domain.models.bank_sync_run import BankSyncRun
from app.domain.models.transaction import Transaction
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.bank_repo import BankRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.services.bank_provider import BankProvider, ProviderExchangeResult, build_bank_provider
from app.domain.services.errors import ForbiddenError, NotFoundError


@dataclass
class BankSyncStats:
    fetched_count: int
    inserted_count: int
    duplicate_count: int
    cursor_before: str | None
    cursor_after: str | None


class BankIntegrationService:
    def __init__(
        self,
        repo: BankRepo,
        audit_repo: AuditRepo,
        tx_repo: TransactionRepo,
        provider: BankProvider | None = None,
    ):
        self.repo = repo
        self.audit_repo = audit_repo
        self.tx_repo = tx_repo
        self.provider = provider or build_bank_provider(get_settings())

    async def list_connections(self, org_id: uuid.UUID) -> list[BankConnection]:
        return await self.repo.list_connections(org_id)

    async def list_accounts(self, org_id: uuid.UUID, connection_id: uuid.UUID) -> list[BankAccount]:
        return await self.repo.get_accounts(org_id=org_id, connection_id=connection_id)

    async def create_link_token(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID) -> dict:
        out = await self.provider.create_link_token(org_id=str(org_id), user_id=str(actor_user_id))
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "bank.plaid.link_token.create",
            "bank_connection",
            str(org_id),
            {"provider": "PLAID"},
        )
        return out

    async def exchange_public_token(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        public_token: str,
        institution_name_override: str | None = None,
    ) -> tuple[BankConnection, list[BankAccount]]:
        exchange = await self.provider.exchange_public_token(public_token=public_token)
        connection = await self._upsert_connection_from_exchange(
            org_id=org_id,
            actor_user_id=actor_user_id,
            exchange=exchange,
            institution_name_override=institution_name_override,
        )
        await self.repo.upsert_cursor(org_id=org_id, connection_id=connection.id, cursor_value=None)
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "bank.plaid.connection.upsert",
            "bank_connection",
            str(connection.id),
            {"provider": connection.provider, "external_item_id": connection.external_item_id},
        )
        accounts = await self.repo.get_accounts(org_id=org_id, connection_id=connection.id)
        return connection, accounts

    async def revoke_connection(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, connection_id: uuid.UUID) -> BankConnection:
        connection = await self.repo.get_connection(connection_id, org_id)
        if not connection:
            raise NotFoundError("Bank connection not found")
        connection.status = "REVOKED"
        connection.revoked_at = datetime.now(tz=timezone.utc)
        connection.access_token_ref = ""
        await self.repo.save_connection(connection)
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "bank.plaid.connection.revoke",
            "bank_connection",
            str(connection.id),
            {"provider": connection.provider},
        )
        return connection

    async def sync_connection(self, *, org_id: uuid.UUID, actor_user_id: uuid.UUID, connection_id: uuid.UUID) -> tuple[BankSyncRun, BankSyncStats]:
        connection = await self.repo.get_connection(connection_id, org_id)
        if not connection:
            raise NotFoundError("Bank connection not found")
        if connection.status != "ACTIVE":
            raise ForbiddenError("Bank connection is not active")
        cursor_row = await self.repo.get_cursor(connection_id=connection_id)
        cursor_before = cursor_row.cursor if cursor_row else None
        run = await self.repo.create_sync_run(
            org_id=org_id,
            connection_id=connection_id,
            triggered_by_user_id=actor_user_id,
            cursor_before=cursor_before,
        )

        fetched_count = 0
        inserted_count = 0
        duplicate_count = 0
        cursor = cursor_before

        try:
            loops = 0
            while loops < 10:
                loops += 1
                batch = await self.provider.sync_transactions(access_token_ref=connection.access_token_ref, cursor=cursor)
                cursor = batch.next_cursor
                rows = [row for row in batch.transactions if not row.pending]
                fetched_count += len(rows)
                ids = [r.external_transaction_id for r in rows]
                existing_ids = await self.repo.existing_external_transaction_ids(
                    connection_id=connection_id, external_transaction_ids=ids
                )
                for row in rows:
                    if row.external_transaction_id in existing_ids:
                        duplicate_count += 1
                        continue
                    tx_type = "EXPENSE" if row.amount >= 0 else "REVENUE"
                    tx_amount = abs(Decimal(row.amount))
                    tx = Transaction(
                        org_id=org_id,
                        date=row.posted_date,
                        amount=tx_amount,
                        type=tx_type,
                        category=row.category or ("Bank Expense" if tx_type == "EXPENSE" else "Bank Revenue"),
                        vendor=row.vendor,
                        notes=f"plaid:{row.external_transaction_id}::{row.name}",
                        created_by=actor_user_id,
                    )
                    await self.tx_repo.create(tx)
                    await self.tx_repo.upsert_monthly_aggregate(org_id, row.posted_date)
                    await self.repo.record_synced_transaction(
                        org_id=org_id,
                        connection_id=connection_id,
                        transaction_id=tx.id,
                        external_transaction_id=row.external_transaction_id,
                        posted_date=row.posted_date,
                        amount=row.amount,
                        currency_code=row.currency_code,
                    )
                    inserted_count += 1
                if not batch.has_more:
                    break

            await self.repo.upsert_cursor(org_id=org_id, connection_id=connection_id, cursor_value=cursor)
            run.status = "SUCCEEDED"
            run.finished_at = datetime.now(tz=timezone.utc)
            run.cursor_after = cursor
            run.fetched_count = fetched_count
            run.inserted_count = inserted_count
            run.duplicate_count = duplicate_count
            await self.repo.save_sync_run(run)
            await self.audit_repo.log(
                actor_user_id,
                org_id,
                "bank.plaid.sync.succeeded",
                "bank_connection",
                str(connection_id),
                {
                    "fetched_count": fetched_count,
                    "inserted_count": inserted_count,
                    "duplicate_count": duplicate_count,
                    "cursor_after": cursor,
                },
            )
            return run, BankSyncStats(
                fetched_count=fetched_count,
                inserted_count=inserted_count,
                duplicate_count=duplicate_count,
                cursor_before=cursor_before,
                cursor_after=cursor,
            )
        except Exception as exc:
            run.status = "FAILED"
            run.finished_at = datetime.now(tz=timezone.utc)
            run.error_message = str(exc)
            run.cursor_after = cursor
            await self.repo.save_sync_run(run)
            connection.last_error = str(exc)
            await self.repo.save_connection(connection)
            await self.audit_repo.log(
                actor_user_id,
                org_id,
                "bank.plaid.sync.failed",
                "bank_connection",
                str(connection_id),
                {"error": str(exc)},
            )
            raise

    async def _upsert_connection_from_exchange(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        exchange: ProviderExchangeResult,
        institution_name_override: str | None,
    ) -> BankConnection:
        connection = await self.repo.get_connection_by_external(
            org_id=org_id,
            provider="PLAID",
            external_item_id=exchange.external_item_id,
        )
        institution_name = institution_name_override or exchange.institution_name
        if connection is None:
            connection = BankConnection(
                org_id=org_id,
                connected_by_user_id=actor_user_id,
                provider="PLAID",
                status="ACTIVE",
                external_item_id=exchange.external_item_id,
                institution_id=exchange.institution_id,
                institution_name=institution_name,
                access_token_ref=exchange.access_token_ref,
                last_error=None,
            )
        else:
            connection.connected_by_user_id = actor_user_id
            connection.status = "ACTIVE"
            connection.external_item_id = exchange.external_item_id
            connection.institution_id = exchange.institution_id
            connection.institution_name = institution_name
            connection.access_token_ref = exchange.access_token_ref
            connection.last_error = None
            connection.revoked_at = None
        connection = await self.repo.save_connection(connection)
        accounts = [
            BankAccount(
                org_id=org_id,
                connection_id=connection.id,
                external_account_id=a.external_account_id,
                name=a.name,
                mask=a.mask,
                account_type=a.account_type,
                account_subtype=a.account_subtype,
                currency_code=a.currency_code,
                is_active=True,
            )
            for a in exchange.accounts
        ]
        await self.repo.replace_accounts(org_id=org_id, connection_id=connection.id, accounts=accounts)
        return connection
