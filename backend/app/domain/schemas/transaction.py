import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.common import TransactionOut


class TransactionCreateIn(BaseModel):
    org_id: uuid.UUID
    date: date_type
    amount: Decimal
    type: str
    category: str
    vendor: str | None = None
    notes: str | None = None


class TransactionUpdateIn(BaseModel):
    date: date_type | None = None
    amount: Decimal | None = None
    category: str | None = None
    vendor: str | None = None
    notes: str | None = None


class TransactionPageOut(BaseModel):
    items: list[TransactionOut]
    page: int
    page_size: int
    total: int


class CSVImportOut(BaseModel):
    import_id: str
    preview: dict
    inserted_count: int


class ImportHistoryItem(BaseModel):
    id: uuid.UUID
    file_name: str
    status: str
    total_rows: int
    inserted_count: int
    duplicate_count: int
    error_count: int
    created_at: datetime
    created_by: uuid.UUID


class ImportHistoryPageOut(BaseModel):
    items: list[ImportHistoryItem]
    page: int
    page_size: int
    total: int


class CSVImportForm(BaseModel):
    org_id: uuid.UUID
    mapping: dict[str, str] = Field(default_factory=dict)


class BulkCategoryRemapIn(BaseModel):
    org_id: uuid.UUID
    from_category: str
    to_category: str
    from_date: date_type | None = None
    to_date: date_type | None = None
