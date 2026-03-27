import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.common import ORMModel


class InventoryItemCreateIn(BaseModel):
    org_id: uuid.UUID
    location_id: uuid.UUID | None = None
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    unit_cost: Decimal = Field(default=Decimal("0"))
    reorder_point: Decimal = Field(default=Decimal("0"))
    is_active: bool = True


class InventoryItemOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    location_id: uuid.UUID | None
    created_by_user_id: uuid.UUID
    sku: str
    name: str
    unit_cost: Decimal
    reorder_point: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryStockEventCreateIn(BaseModel):
    org_id: uuid.UUID
    item_id: uuid.UUID
    location_id: uuid.UUID | None = None
    event_type: str = Field(min_length=1, max_length=16)
    quantity: Decimal
    unit_cost: Decimal | None = None
    occurred_at: datetime | None = None
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class InventoryStockEventOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_id: uuid.UUID
    location_id: uuid.UUID | None
    event_type: str
    quantity: Decimal
    delta_qty: Decimal
    unit_cost: Decimal | None
    occurred_at: datetime
    reference: str | None
    notes: str | None
    created_by_user_id: uuid.UUID
    created_at: datetime


class InventoryPurchaseOrderCreateIn(BaseModel):
    org_id: uuid.UUID
    item_id: uuid.UUID
    location_id: uuid.UUID | None = None
    quantity: Decimal
    unit_cost: Decimal | None = None
    expected_date: date
    external_ref: str | None = Field(default=None, max_length=120)


class InventoryPurchaseOrderOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_id: uuid.UUID
    location_id: uuid.UUID | None
    quantity: Decimal
    received_qty: Decimal
    unit_cost: Decimal | None
    expected_date: date
    status: str
    external_ref: str | None
    created_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InventoryForecastItemOut(ORMModel):
    item_id: uuid.UUID
    sku: str
    name: str
    location_id: uuid.UUID | None
    on_hand_qty: Decimal
    inbound_open_qty: Decimal
    units_per_day: Decimal
    days_of_cover: Decimal | None
    projected_stockout_date: date | None
    risk_level: str
    reorder_point: Decimal
    cogs_exposure_30d: Decimal


class InventoryForecastOut(BaseModel):
    generated_at: datetime
    lookback_days: int
    horizon_days: int
    items: list[InventoryForecastItemOut]
    high_risk_items: int
