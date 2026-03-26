import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.bank_account import BankAccount
from app.domain.models.bank_connection import BankConnection
from app.domain.models.bank_sync_cursor import BankSyncCursor
from app.domain.models.bank_sync_run import BankSyncRun
from app.domain.models.bank_synced_transaction import BankSyncedTransaction


class BankRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_connections(self, org_id: uuid.UUID) -> list[BankConnection]:
        q = await self.db.execute(
            select(BankConnection).where(BankConnection.org_id == org_id).order_by(BankConnection.created_at.desc())
        )
        return list(q.scalars().all())

    async def get_connection(self, connection_id: uuid.UUID, org_id: uuid.UUID) -> BankConnection | None:
        q = await self.db.execute(
            select(BankConnection).where(BankConnection.id == connection_id, BankConnection.org_id == org_id)
        )
        return q.scalar_one_or_none()

    async def get_connection_by_external(
        self, *, org_id: uuid.UUID, provider: str, external_item_id: str
    ) -> BankConnection | None:
        q = await self.db.execute(
            select(BankConnection).where(
                BankConnection.org_id == org_id,
                BankConnection.provider == provider,
                BankConnection.external_item_id == external_item_id,
            )
        )
        return q.scalar_one_or_none()

    async def save_connection(self, connection: BankConnection) -> BankConnection:
        self.db.add(connection)
        await self.db.flush()
        return connection

    async def list_active_connections_by_external_item(self, *, provider: str, external_item_id: str) -> list[BankConnection]:
        q = await self.db.execute(
            select(BankConnection).where(
                BankConnection.provider == provider,
                BankConnection.external_item_id == external_item_id,
                BankConnection.status == "ACTIVE",
            )
        )
        return list(q.scalars().all())

    async def list_active_connections(self) -> list[BankConnection]:
        q = await self.db.execute(
            select(BankConnection).where(BankConnection.status == "ACTIVE").order_by(BankConnection.created_at.asc())
        )
        return list(q.scalars().all())

    async def replace_accounts(self, *, org_id: uuid.UUID, connection_id: uuid.UUID, accounts: list[BankAccount]) -> None:
        await self.db.execute(
            delete(BankAccount).where(BankAccount.org_id == org_id, BankAccount.connection_id == connection_id)
        )
        for account in accounts:
            self.db.add(account)
        await self.db.flush()

    async def get_accounts(self, *, org_id: uuid.UUID, connection_id: uuid.UUID) -> list[BankAccount]:
        q = await self.db.execute(
            select(BankAccount)
            .where(BankAccount.org_id == org_id, BankAccount.connection_id == connection_id)
            .order_by(BankAccount.created_at.asc())
        )
        return list(q.scalars().all())

    async def get_cursor(self, *, connection_id: uuid.UUID) -> BankSyncCursor | None:
        q = await self.db.execute(select(BankSyncCursor).where(BankSyncCursor.connection_id == connection_id))
        return q.scalar_one_or_none()

    async def upsert_cursor(
        self,
        *,
        org_id: uuid.UUID,
        connection_id: uuid.UUID,
        cursor_value: str | None,
    ) -> BankSyncCursor:
        row = await self.get_cursor(connection_id=connection_id)
        now = datetime.now(tz=timezone.utc)
        if row is None:
            row = BankSyncCursor(
                org_id=org_id,
                connection_id=connection_id,
                cursor=cursor_value,
                last_synced_at=now if cursor_value is not None else None,
            )
        else:
            row.cursor = cursor_value
            row.last_synced_at = now if cursor_value is not None else row.last_synced_at
        self.db.add(row)
        await self.db.flush()
        return row

    async def create_sync_run(
        self,
        *,
        org_id: uuid.UUID,
        connection_id: uuid.UUID,
        triggered_by_user_id: uuid.UUID | None,
        cursor_before: str | None,
    ) -> BankSyncRun:
        row = BankSyncRun(
            org_id=org_id,
            connection_id=connection_id,
            triggered_by_user_id=triggered_by_user_id,
            status="RUNNING",
            cursor_before=cursor_before,
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def save_sync_run(self, run: BankSyncRun) -> BankSyncRun:
        self.db.add(run)
        await self.db.flush()
        return run

    async def existing_external_transaction_ids(
        self,
        *,
        connection_id: uuid.UUID,
        external_transaction_ids: list[str],
    ) -> set[str]:
        if not external_transaction_ids:
            return set()
        q = await self.db.execute(
            select(BankSyncedTransaction.external_transaction_id).where(
                BankSyncedTransaction.connection_id == connection_id,
                BankSyncedTransaction.external_transaction_id.in_(external_transaction_ids),
            )
        )
        return {row[0] for row in q.all()}

    async def record_synced_transaction(
        self,
        *,
        org_id: uuid.UUID,
        connection_id: uuid.UUID,
        transaction_id: uuid.UUID | None,
        external_transaction_id: str,
        posted_date,
        amount: Decimal | None,
        currency_code: str | None,
    ) -> BankSyncedTransaction:
        row = BankSyncedTransaction(
            org_id=org_id,
            connection_id=connection_id,
            transaction_id=transaction_id,
            external_transaction_id=external_transaction_id,
            posted_date=posted_date,
            amount=amount,
            currency_code=currency_code,
        )
        self.db.add(row)
        await self.db.flush()
        return row
