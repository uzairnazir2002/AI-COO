import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.common import ORMModel


class BudgetCreateIn(BaseModel):
    org_id: uuid.UUID
    category: str = Field(min_length=1, max_length=120)
    period_month: date
    budget_type: str = Field(default="EXPENSE")
    planned_amount: Decimal
    notes: str | None = None


class BudgetUpdateIn(BaseModel):
    org_id: uuid.UUID
    planned_amount: Decimal
    notes: str | None = None


class BudgetOut(ORMModel):
    id: uuid.UUID
    org_id: uuid.UUID
    created_by_user_id: uuid.UUID
    category: str
    period_month: date
    budget_type: str
    planned_amount: Decimal
    notes: str | None
    version: int
    is_current: bool
    created_at: datetime
    updated_at: datetime


class BudgetVarianceLineOut(BaseModel):
    category: str
    budget_type: str
    planned_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal
    variance_pct: Decimal | None = None


class BudgetVarianceTotalsOut(BaseModel):
    planned_amount: Decimal
    actual_amount: Decimal
    variance_amount: Decimal


class BudgetVarianceOut(BaseModel):
    org_id: uuid.UUID
    period_month: date
    budget_type: str
    totals: BudgetVarianceTotalsOut
    lines: list[BudgetVarianceLineOut]
