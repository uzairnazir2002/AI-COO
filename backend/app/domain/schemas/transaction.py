import uuid
from datetime import date as date_type
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


class CSVImportForm(BaseModel):
    org_id: uuid.UUID
    mapping: dict[str, str] = Field(default_factory=dict)


class BulkCategoryRemapIn(BaseModel):
    org_id: uuid.UUID
    from_category: str
    to_category: str
    from_date: date_type | None = None
    to_date: date_type | None = None
