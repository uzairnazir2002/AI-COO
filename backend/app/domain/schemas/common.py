import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TransactionOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    date: date
    amount: Decimal
    type: str
    category: str
    vendor: str | None
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime
