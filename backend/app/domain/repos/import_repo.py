import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.transaction_import import TransactionImport


class ImportRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, record: TransactionImport) -> TransactionImport:
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_imports(self, org_id: uuid.UUID, page: int, page_size: int) -> tuple[list[TransactionImport], int]:
        q = (
            select(TransactionImport)
            .where(TransactionImport.org_id == org_id)
            .order_by(TransactionImport.created_at.desc())
        )
        total_q = select(func.count()).select_from(TransactionImport).where(TransactionImport.org_id == org_id)
        rows = await self.db.execute(q.offset((page - 1) * page_size).limit(page_size))
        total = await self.db.scalar(total_q)
        return list(rows.scalars().all()), int(total or 0)

    async def get(self, import_id: uuid.UUID, org_id: uuid.UUID) -> TransactionImport | None:
        q = await self.db.execute(
            select(TransactionImport).where(TransactionImport.id == import_id, TransactionImport.org_id == org_id)
        )
        return q.scalar_one_or_none()
