import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ForecastPoint(BaseModel):
    month: date
    revenue_pred: Decimal
    expense_pred: Decimal
    confidence_low: Decimal
    confidence_high: Decimal


class ForecastOut(BaseModel):
    scenarios: dict[str, list[ForecastPoint]]
    generated_at: datetime


class ForecastOverrideIn(BaseModel):
    org_id: uuid.UUID
    month: date
    revenue_override: Decimal | None = None
    expense_override: Decimal | None = None
    scenario: str
