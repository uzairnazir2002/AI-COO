from datetime import date
from decimal import Decimal
import uuid

from pydantic import BaseModel


class SummaryOut(BaseModel):
    cash_balance: Decimal
    revenue_mtd: Decimal
    expenses_mtd: Decimal
    net_profit_mtd: Decimal
    burn_rate_monthly: Decimal
    alerts_count_open: int


class CashPoint(BaseModel):
    date: date
    revenue: Decimal
    expense: Decimal
    net: Decimal


class CashflowOut(BaseModel):
    points: list[CashPoint]


class RunwayOut(BaseModel):
    runway_days: int
    monthly_burn: Decimal
    cash_balance: Decimal
    alert: bool


class AnalyticsRecomputeOut(BaseModel):
    ok: bool
    job_id: str
    status: str
    result: dict | None = None


class LocationBenchmarkTotalsOut(BaseModel):
    revenue: Decimal
    expense: Decimal
    net: Decimal


class LocationBenchmarkItemOut(BaseModel):
    location_id: uuid.UUID | None = None
    location_name: str
    transaction_count: int
    revenue: Decimal
    expense: Decimal
    net: Decimal
    margin_pct: Decimal | None = None
    revenue_share_pct: Decimal | None = None
    expense_share_pct: Decimal | None = None


class LocationBenchmarkOut(BaseModel):
    org_id: uuid.UUID
    from_date: date
    to_date: date
    totals: LocationBenchmarkTotalsOut
    locations: list[LocationBenchmarkItemOut]
