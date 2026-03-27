from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.domain.services.inventory_service import InventoryService


@dataclass
class _Item:
    id: UUID
    org_id: UUID
    location_id: UUID | None
    created_by_user_id: UUID
    sku: str
    name: str
    unit_cost: Decimal
    reorder_point: Decimal
    is_active: bool


@dataclass
class _StockLevel:
    on_hand_qty: Decimal


class _Repo:
    def __init__(self):
        self.items: list[_Item] = []
        self.stock_levels: dict[tuple[UUID, UUID | None], Decimal] = {}
        self.outbound: dict[tuple[UUID, UUID | None], Decimal] = {}
        self.open_po: dict[tuple[UUID, UUID | None], Decimal] = {}

    async def list_items(self, org_id, include_inactive=False, location_id=None):
        rows = [item for item in self.items if item.org_id == org_id]
        if not include_inactive:
            rows = [item for item in rows if item.is_active]
        if location_id is not None:
            rows = [item for item in rows if item.location_id == location_id]
        return rows

    async def get_item(self, org_id, item_id):
        for item in self.items:
            if item.org_id == org_id and item.id == item_id:
                return item
        return None

    async def get_item_by_sku(self, org_id, sku, location_id):
        for item in self.items:
            if item.org_id == org_id and item.sku == sku and item.location_id == location_id:
                return item
        return None

    async def create_item(self, item):
        out = _Item(
            id=uuid4(),
            org_id=item.org_id,
            location_id=item.location_id,
            created_by_user_id=item.created_by_user_id,
            sku=item.sku,
            name=item.name,
            unit_cost=Decimal(item.unit_cost),
            reorder_point=Decimal(item.reorder_point),
            is_active=item.is_active,
        )
        self.items.append(out)
        return out

    async def get_stock_level(self, org_id, item_id, location_id, for_update=False):
        _ = (org_id, for_update)
        qty = self.stock_levels.get((item_id, location_id))
        if qty is None:
            return None
        return _StockLevel(on_hand_qty=qty)

    async def upsert_stock_level(self, org_id, item_id, location_id, delta_qty):
        _ = org_id
        current = self.stock_levels.get((item_id, location_id), Decimal("0"))
        next_qty = current + Decimal(delta_qty)
        self.stock_levels[(item_id, location_id)] = next_qty
        return _StockLevel(on_hand_qty=next_qty)

    async def create_stock_event(self, event):
        return event

    async def create_purchase_order(self, row):
        return row

    async def outbound_quantity(self, org_id, item_id, location_id, from_dt, to_dt):
        _ = (org_id, from_dt, to_dt)
        return self.outbound.get((item_id, location_id), Decimal("0"))

    async def open_purchase_quantity(self, org_id, item_id, location_id, horizon_date):
        _ = (org_id, horizon_date)
        return self.open_po.get((item_id, location_id), Decimal("0"))

    async def upsert_sales_velocity(self, **kwargs):
        return kwargs


@pytest.mark.asyncio
async def test_create_item_normalizes_and_rejects_duplicates():
    repo = _Repo()
    svc = InventoryService(repo)  # type: ignore[arg-type]
    org_id = uuid4()
    user_id = uuid4()

    first = await svc.create_item(
        org_id=org_id,
        actor_user_id=user_id,
        sku=" sku-01 ",
        name=" Widget A ",
        unit_cost=Decimal("2.99"),
        reorder_point=Decimal("10"),
    )
    assert first.sku == "SKU-01"
    assert first.name == "Widget A"

    with pytest.raises(ValueError, match="SKU already exists"):
        await svc.create_item(
            org_id=org_id,
            actor_user_id=user_id,
            sku="SKU-01",
            name="Widget duplicate",
            unit_cost=Decimal("3.10"),
            reorder_point=Decimal("11"),
        )


@pytest.mark.asyncio
async def test_record_stock_event_updates_stock_level():
    repo = _Repo()
    org_id = uuid4()
    user_id = uuid4()
    item = _Item(
        id=uuid4(),
        org_id=org_id,
        location_id=None,
        created_by_user_id=user_id,
        sku="W-001",
        name="Widget",
        unit_cost=Decimal("5.00"),
        reorder_point=Decimal("8"),
        is_active=True,
    )
    repo.items.append(item)
    svc = InventoryService(repo)  # type: ignore[arg-type]

    event, on_hand = await svc.record_stock_event(
        org_id=org_id,
        actor_user_id=user_id,
        item_id=item.id,
        event_type="INBOUND",
        quantity=Decimal("12"),
    )
    assert event.delta_qty == Decimal("12.000")
    assert on_hand == Decimal("12.000")

    _, on_hand_after = await svc.record_stock_event(
        org_id=org_id,
        actor_user_id=user_id,
        item_id=item.id,
        event_type="OUTBOUND",
        quantity=Decimal("5"),
    )
    assert on_hand_after == Decimal("7.000")


@pytest.mark.asyncio
async def test_forecast_marks_high_risk_when_cover_is_short():
    repo = _Repo()
    org_id = uuid4()
    user_id = uuid4()
    item = _Item(
        id=uuid4(),
        org_id=org_id,
        location_id=None,
        created_by_user_id=user_id,
        sku="SKU-HIGH",
        name="High risk item",
        unit_cost=Decimal("10.00"),
        reorder_point=Decimal("20"),
        is_active=True,
    )
    repo.items.append(item)
    repo.stock_levels[(item.id, None)] = Decimal("5.000")
    repo.outbound[(item.id, None)] = Decimal("30.000")
    repo.open_po[(item.id, None)] = Decimal("0.000")
    svc = InventoryService(repo)  # type: ignore[arg-type]

    out = await svc.forecast(org_id=org_id, lookback_days=30, horizon_days=30)

    assert out["high_risk_items"] == 1
    line = out["items"][0]
    assert line.risk_level == "HIGH"
    assert line.units_per_day == Decimal("1.0000")
    assert line.days_of_cover == Decimal("5.0")
    assert line.projected_stockout_date <= (
        datetime.now(tz=timezone.utc).date() + timedelta(days=6)
    )
