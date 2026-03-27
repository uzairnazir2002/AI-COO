from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.inventory_item import InventoryItem
from app.domain.models.inventory_purchase_order import InventoryPurchaseOrder
from app.domain.models.inventory_sales_velocity import InventorySalesVelocity
from app.domain.models.inventory_stock_event import InventoryStockEvent
from app.domain.models.inventory_stock_level import InventoryStockLevel


def _location_filter(column, location_id: uuid.UUID | None):
    if location_id is None:
        return column.is_(None)
    return column == location_id


class InventoryRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_items(
        self,
        *,
        org_id: uuid.UUID,
        include_inactive: bool = False,
        location_id: uuid.UUID | None = None,
    ) -> list[InventoryItem]:
        query = select(InventoryItem).where(InventoryItem.org_id == org_id)
        if not include_inactive:
            query = query.where(InventoryItem.is_active.is_(True))
        if location_id is not None:
            query = query.where(InventoryItem.location_id == location_id)
        query = query.order_by(InventoryItem.name.asc())
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def get_item(self, *, org_id: uuid.UUID, item_id: uuid.UUID) -> InventoryItem | None:
        row = await self.db.execute(
            select(InventoryItem).where(InventoryItem.org_id == org_id, InventoryItem.id == item_id)
        )
        return row.scalar_one_or_none()

    async def get_item_by_sku(
        self, *, org_id: uuid.UUID, sku: str, location_id: uuid.UUID | None
    ) -> InventoryItem | None:
        row = await self.db.execute(
            select(InventoryItem).where(
                InventoryItem.org_id == org_id,
                InventoryItem.sku == sku,
                _location_filter(InventoryItem.location_id, location_id),
            )
        )
        return row.scalar_one_or_none()

    async def create_item(self, item: InventoryItem) -> InventoryItem:
        self.db.add(item)
        await self.db.flush()
        return item

    async def get_stock_level(
        self,
        *,
        org_id: uuid.UUID,
        item_id: uuid.UUID,
        location_id: uuid.UUID | None,
        for_update: bool = False,
    ) -> InventoryStockLevel | None:
        query = select(InventoryStockLevel).where(
            InventoryStockLevel.org_id == org_id,
            InventoryStockLevel.item_id == item_id,
            _location_filter(InventoryStockLevel.location_id, location_id),
        )
        if for_update:
            query = query.with_for_update()
        row = await self.db.execute(
            query.order_by(InventoryStockLevel.updated_at.desc(), InventoryStockLevel.id.desc())
        )
        matches = list(row.scalars().all())
        return matches[0] if matches else None

    async def upsert_stock_level(
        self,
        *,
        org_id: uuid.UUID,
        item_id: uuid.UUID,
        location_id: uuid.UUID | None,
        delta_qty: Decimal,
    ) -> InventoryStockLevel:
        stock = await self.get_stock_level(
            org_id=org_id,
            item_id=item_id,
            location_id=location_id,
            for_update=True,
        )
        if stock is None:
            stock = InventoryStockLevel(
                org_id=org_id,
                item_id=item_id,
                location_id=location_id,
                on_hand_qty=Decimal("0"),
                reserved_qty=Decimal("0"),
            )
        stock.on_hand_qty = Decimal(stock.on_hand_qty) + Decimal(delta_qty)
        self.db.add(stock)
        await self.db.flush()
        return stock

    async def create_stock_event(self, event: InventoryStockEvent) -> InventoryStockEvent:
        self.db.add(event)
        await self.db.flush()
        return event

    async def outbound_quantity(
        self,
        *,
        org_id: uuid.UUID,
        item_id: uuid.UUID,
        location_id: uuid.UUID | None,
        from_dt: datetime,
        to_dt: datetime,
    ) -> Decimal:
        query = await self.db.execute(
            select(func.coalesce(func.sum(-InventoryStockEvent.delta_qty), 0))
            .where(
                InventoryStockEvent.org_id == org_id,
                InventoryStockEvent.item_id == item_id,
                _location_filter(InventoryStockEvent.location_id, location_id),
                InventoryStockEvent.delta_qty < 0,
                InventoryStockEvent.occurred_at >= from_dt,
                InventoryStockEvent.occurred_at <= to_dt,
            )
        )
        return Decimal(query.scalar_one())

    async def create_purchase_order(self, row: InventoryPurchaseOrder) -> InventoryPurchaseOrder:
        self.db.add(row)
        await self.db.flush()
        return row

    async def open_purchase_quantity(
        self,
        *,
        org_id: uuid.UUID,
        item_id: uuid.UUID,
        location_id: uuid.UUID | None,
        horizon_date: date,
    ) -> Decimal:
        q = await self.db.execute(
            select(func.coalesce(func.sum(InventoryPurchaseOrder.quantity - InventoryPurchaseOrder.received_qty), 0)).where(
                InventoryPurchaseOrder.org_id == org_id,
                InventoryPurchaseOrder.item_id == item_id,
                _location_filter(InventoryPurchaseOrder.location_id, location_id),
                InventoryPurchaseOrder.status.in_(["OPEN", "PARTIAL"]),
                InventoryPurchaseOrder.expected_date <= horizon_date,
                InventoryPurchaseOrder.quantity > InventoryPurchaseOrder.received_qty,
            )
        )
        return Decimal(q.scalar_one())

    async def upsert_sales_velocity(
        self,
        *,
        org_id: uuid.UUID,
        item_id: uuid.UUID,
        location_id: uuid.UUID | None,
        window_days: int,
        units_per_day: Decimal,
        basis_start: date,
        basis_end: date,
    ) -> InventorySalesVelocity:
        query = await self.db.execute(
            select(InventorySalesVelocity).where(
                InventorySalesVelocity.org_id == org_id,
                InventorySalesVelocity.item_id == item_id,
                _location_filter(InventorySalesVelocity.location_id, location_id),
                InventorySalesVelocity.window_days == window_days,
            )
        )
        matches = list(query.scalars().all())
        row = matches[0] if matches else None
        if row is None:
            row = InventorySalesVelocity(
                org_id=org_id,
                item_id=item_id,
                location_id=location_id,
                window_days=window_days,
                units_per_day=units_per_day,
                basis_start=basis_start,
                basis_end=basis_end,
            )
        else:
            row.units_per_day = units_per_day
            row.basis_start = basis_start
            row.basis_end = basis_end
        self.db.add(row)
        await self.db.flush()
        return row
