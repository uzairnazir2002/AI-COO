from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.services.alerts_service import AlertsService


@pytest.mark.asyncio
async def test_inventory_stockout_detection_creates_high_risk_alert(monkeypatch):
    org_id = uuid4()
    item_id = uuid4()
    service = AlertsService(db=SimpleNamespace(), repo=SimpleNamespace())  # type: ignore[arg-type]

    captured = []

    async def fake_create_if_new(alert, **_kwargs):
        captured.append(alert)
        return 1

    async def fake_forecast(self, **_kwargs):  # noqa: ARG001
        return {
            "items": [
                {
                    "item_id": str(item_id),
                    "sku": "SKU-RISK",
                    "name": "Risk item",
                    "location_id": None,
                    "risk_level": "HIGH",
                    "days_of_cover": "5.0",
                    "projected_stockout_date": "2026-04-01",
                    "on_hand_qty": "3.000",
                    "reorder_point": "10.000",
                    "units_per_day": "1.0000",
                    "cogs_exposure_30d": "300.00",
                }
            ]
        }

    monkeypatch.setattr(service, "_create_if_new", fake_create_if_new)
    monkeypatch.setattr("app.domain.services.alerts_service.InventoryService.forecast", fake_forecast)

    created = await service._detect_inventory_stockout_risk(org_id, location=None)

    assert created == 1
    assert len(captured) == 1
    alert = captured[0]
    assert alert.kind == "ANOMALY"
    assert alert.severity == "HIGH"
    assert "Inventory stockout risk" in alert.title
    assert alert.meta["subkind"] == "INVENTORY_STOCKOUT"
    assert Decimal(str(alert.meta["impact"])) == Decimal("300.00")
