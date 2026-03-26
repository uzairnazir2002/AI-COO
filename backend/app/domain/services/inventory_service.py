from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.domain.models.inventory_item import InventoryItem
from app.domain.models.inventory_purchase_order import InventoryPurchaseOrder
from app.domain.models.inventory_stock_event import InventoryStockEvent
from app.domain.repos.inventory_repo import InventoryRepo
from app.domain.services.errors import NotFoundError


VALID_EVENT_TYPES = {"INBOUND", "OUTBOUND", "ADJUSTMENT"}
VALID_PO_STATUSES = {"OPEN", "PARTIAL", "RECEIVED", "CANCELLED"}


@dataclass
class ForecastLine:
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


class InventoryService:
    def __init__(self, repo: InventoryRepo):
        self.repo = repo

    @staticmethod
    def _normalize_sku(sku: str) -> str:
        normalized = sku.strip().upper()
        if not normalized:
            raise ValueError("SKU is required")
        return normalized

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Item name is required")
        return normalized

    @staticmethod
    def _normalize_non_negative(value: Decimal, label: str, scale: str = "0.001") -> Decimal:
        out = Decimal(value).quantize(Decimal(scale), rounding=ROUND_HALF_UP)
        if out < 0:
            raise ValueError(f"{label} cannot be negative")
        return out

    @staticmethod
    def _event_delta(event_type: str, quantity: Decimal) -> Decimal:
        qty = Decimal(quantity).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        if event_type in {"INBOUND", "OUTBOUND"} and qty <= 0:
            raise ValueError("Quantity must be greater than zero for inbound/outbound events")
        if event_type == "ADJUSTMENT" and qty == 0:
            raise ValueError("Adjustment quantity cannot be zero")
        if event_type == "INBOUND":
            return abs(qty)
        if event_type == "OUTBOUND":
            return -abs(qty)
        return qty

    async def list_items(
        self,
        *,
        org_id: uuid.UUID,
        include_inactive: bool = False,
        location_id: uuid.UUID | None = None,
    ) -> list[InventoryItem]:
        return await self.repo.list_items(org_id=org_id, include_inactive=include_inactive, location_id=location_id)

    async def create_item(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        sku: str,
        name: str,
        unit_cost: Decimal,
        reorder_point: Decimal,
        location_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> InventoryItem:
        normalized_sku = self._normalize_sku(sku)
        normalized_name = self._normalize_name(name)
        normalized_unit_cost = self._normalize_non_negative(unit_cost, "Unit cost", scale="0.01")
        normalized_reorder_point = self._normalize_non_negative(reorder_point, "Reorder point", scale="0.001")
        existing = await self.repo.get_item_by_sku(org_id=org_id, sku=normalized_sku, location_id=location_id)
        if existing is not None:
            raise ValueError("SKU already exists for this location scope")
        return await self.repo.create_item(
            InventoryItem(
                org_id=org_id,
                created_by_user_id=actor_user_id,
                location_id=location_id,
                sku=normalized_sku,
                name=normalized_name,
                unit_cost=normalized_unit_cost,
                reorder_point=normalized_reorder_point,
                is_active=is_active,
            )
        )

    async def record_stock_event(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        item_id: uuid.UUID,
        event_type: str,
        quantity: Decimal,
        location_id: uuid.UUID | None = None,
        unit_cost: Decimal | None = None,
        occurred_at: datetime | None = None,
        reference: str | None = None,
        notes: str | None = None,
    ) -> tuple[InventoryStockEvent, Decimal]:
        item = await self.repo.get_item(org_id=org_id, item_id=item_id)
        if item is None:
            raise NotFoundError("Inventory item not found")
        normalized_type = event_type.strip().upper()
        if normalized_type not in VALID_EVENT_TYPES:
            raise ValueError("Unsupported stock event type")
        if item.location_id is not None and location_id not in {None, item.location_id}:
            raise ValueError("Item is scoped to a different location")
        scoped_location = item.location_id if item.location_id is not None else location_id
        delta_qty = self._event_delta(normalized_type, quantity)
        normalized_unit_cost = None
        if unit_cost is not None:
            normalized_unit_cost = self._normalize_non_negative(unit_cost, "Unit cost", scale="0.01")
        stock = await self.repo.upsert_stock_level(
            org_id=org_id,
            item_id=item_id,
            location_id=scoped_location,
            delta_qty=delta_qty,
        )
        event = await self.repo.create_stock_event(
            InventoryStockEvent(
                org_id=org_id,
                item_id=item_id,
                location_id=scoped_location,
                created_by_user_id=actor_user_id,
                event_type=normalized_type,
                quantity=Decimal(quantity).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
                delta_qty=delta_qty,
                unit_cost=normalized_unit_cost,
                occurred_at=occurred_at or datetime.now(tz=timezone.utc),
                reference=reference.strip() if isinstance(reference, str) and reference.strip() else None,
                notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
            )
        )
        return event, Decimal(stock.on_hand_qty)

    async def create_purchase_order(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        item_id: uuid.UUID,
        quantity: Decimal,
        expected_date: date,
        location_id: uuid.UUID | None = None,
        unit_cost: Decimal | None = None,
        external_ref: str | None = None,
        status: str = "OPEN",
    ) -> InventoryPurchaseOrder:
        item = await self.repo.get_item(org_id=org_id, item_id=item_id)
        if item is None:
            raise NotFoundError("Inventory item not found")
        normalized_quantity = self._normalize_non_negative(quantity, "Quantity", scale="0.001")
        if normalized_quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        normalized_status = status.strip().upper()
        if normalized_status not in VALID_PO_STATUSES:
            raise ValueError("Unsupported purchase order status")
        normalized_unit_cost = None
        if unit_cost is not None:
            normalized_unit_cost = self._normalize_non_negative(unit_cost, "Unit cost", scale="0.01")
        scoped_location = item.location_id if item.location_id is not None else location_id
        return await self.repo.create_purchase_order(
            InventoryPurchaseOrder(
                org_id=org_id,
                item_id=item_id,
                location_id=scoped_location,
                created_by_user_id=actor_user_id,
                quantity=normalized_quantity,
                received_qty=Decimal("0"),
                unit_cost=normalized_unit_cost,
                expected_date=expected_date,
                status=normalized_status,
                external_ref=external_ref.strip() if isinstance(external_ref, str) and external_ref.strip() else None,
            )
        )

    async def forecast(
        self,
        *,
        org_id: uuid.UUID,
        lookback_days: int = 30,
        horizon_days: int = 30,
        location_id: uuid.UUID | None = None,
    ) -> dict:
        if lookback_days <= 0 or lookback_days > 365:
            raise ValueError("lookback_days must be between 1 and 365")
        if horizon_days <= 0 or horizon_days > 365:
            raise ValueError("horizon_days must be between 1 and 365")

        now = datetime.now(tz=timezone.utc)
        basis_start_dt = now - timedelta(days=lookback_days)
        basis_start_date = basis_start_dt.date()
        basis_end_date = now.date()
        horizon_date = now.date() + timedelta(days=horizon_days)

        rows = await self.repo.list_items(org_id=org_id, include_inactive=False, location_id=location_id)
        lines: list[ForecastLine] = []
        high_risk_items = 0
        for item in rows:
            scoped_location = item.location_id if item.location_id is not None else location_id
            stock_level = await self.repo.get_stock_level(
                org_id=org_id,
                item_id=item.id,
                location_id=scoped_location,
            )
            on_hand_qty = Decimal(stock_level.on_hand_qty if stock_level is not None else Decimal("0")).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
            outbound_qty = await self.repo.outbound_quantity(
                org_id=org_id,
                item_id=item.id,
                location_id=scoped_location,
                from_dt=basis_start_dt,
                to_dt=now,
            )
            units_per_day = (outbound_qty / Decimal(lookback_days)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            await self.repo.upsert_sales_velocity(
                org_id=org_id,
                item_id=item.id,
                location_id=scoped_location,
                window_days=lookback_days,
                units_per_day=units_per_day,
                basis_start=basis_start_date,
                basis_end=basis_end_date,
            )
            inbound_open_qty = await self.repo.open_purchase_quantity(
                org_id=org_id,
                item_id=item.id,
                location_id=scoped_location,
                horizon_date=horizon_date,
            )
            effective_qty = on_hand_qty + inbound_open_qty
            days_of_cover: Decimal | None
            projected_stockout_date: date | None
            if units_per_day <= 0:
                days_of_cover = None
                projected_stockout_date = None
            else:
                days_cover_float = float(effective_qty / units_per_day)
                if days_cover_float < 0:
                    days_cover_float = 0
                days_of_cover = Decimal(days_cover_float).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
                projected_stockout_date = now.date() + timedelta(days=math.ceil(days_cover_float))

            reorder_point = Decimal(item.reorder_point).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            risk_level = "LOW"
            if units_per_day > 0:
                if days_of_cover is not None and days_of_cover <= Decimal("14.0"):
                    risk_level = "HIGH"
                elif days_of_cover is not None and days_of_cover <= Decimal("30.0"):
                    risk_level = "MEDIUM"
            if effective_qty < reorder_point:
                risk_level = "HIGH" if risk_level != "HIGH" else risk_level

            if risk_level == "HIGH":
                high_risk_items += 1

            cogs_exposure_30d = (units_per_day * Decimal("30") * Decimal(item.unit_cost)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            lines.append(
                ForecastLine(
                    item_id=item.id,
                    sku=item.sku,
                    name=item.name,
                    location_id=scoped_location,
                    on_hand_qty=on_hand_qty,
                    inbound_open_qty=Decimal(inbound_open_qty).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
                    units_per_day=units_per_day,
                    days_of_cover=days_of_cover,
                    projected_stockout_date=projected_stockout_date,
                    risk_level=risk_level,
                    reorder_point=reorder_point,
                    cogs_exposure_30d=cogs_exposure_30d,
                )
            )
        return {
            "generated_at": now,
            "lookback_days": lookback_days,
            "horizon_days": horizon_days,
            "items": lines,
            "high_risk_items": high_risk_items,
        }
