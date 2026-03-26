from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.domain.services.alerts_service as alerts_module
from app.domain.services.alerts_service import AlertsService


@pytest.mark.asyncio
async def test_detect_budget_threshold_creates_persistent_alert_with_audit_metadata(monkeypatch):
    class _FakeBudgetService:
        def __init__(self, _repo):
            pass

        async def budget_variance(self, *, org_id, period_month, budget_type, location_id=None):
            _ = (org_id, period_month, budget_type, location_id)
            return {
                "lines": [
                    SimpleNamespace(
                        category="Marketing",
                        planned_amount=Decimal("100.00"),
                        actual_amount=Decimal("140.00"),
                        variance_amount=Decimal("40.00"),
                        variance_pct=Decimal("40.00"),
                    )
                ]
            }

    monkeypatch.setattr(alerts_module, "BudgetService", _FakeBudgetService)
    service = AlertsService(db=object(), repo=SimpleNamespace())  # type: ignore[arg-type]
    captured = []

    async def _fake_create_if_new(alert, **kwargs):
        captured.append((alert, kwargs))
        return 1

    monkeypatch.setattr(service, "_create_if_new", _fake_create_if_new)
    created = await service._detect_budget_threshold(uuid4(), Decimal("10.00"), location=None)

    assert created == 1
    assert len(captured) == 1
    alert, kwargs = captured[0]
    assert alert.kind == "PROFIT_LEAK"
    assert alert.meta["subkind"] == "BUDGET_THRESHOLD"
    assert Decimal(str(alert.meta["variance_pct"])) == Decimal("40.00")
    assert Decimal(str(alert.meta["threshold_pct"])) == Decimal("10.00")
    assert kwargs["audit_action"] == "alert.detect.budget_threshold"
    assert kwargs["audit_metadata"]["category"] == "Marketing"


@pytest.mark.asyncio
async def test_detect_budget_threshold_ignores_rows_below_threshold(monkeypatch):
    class _FakeBudgetService:
        def __init__(self, _repo):
            pass

        async def budget_variance(self, *, org_id, period_month, budget_type, location_id=None):
            _ = (org_id, period_month, budget_type, location_id)
            return {
                "lines": [
                    SimpleNamespace(
                        category="Ops",
                        planned_amount=Decimal("500.00"),
                        actual_amount=Decimal("520.00"),
                        variance_amount=Decimal("20.00"),
                        variance_pct=Decimal("4.00"),
                    )
                ]
            }

    monkeypatch.setattr(alerts_module, "BudgetService", _FakeBudgetService)
    service = AlertsService(db=object(), repo=SimpleNamespace())  # type: ignore[arg-type]
    invoked = False

    async def _fake_create_if_new(_alert, **_kwargs):
        nonlocal invoked
        invoked = True
        return 1

    monkeypatch.setattr(service, "_create_if_new", _fake_create_if_new)
    created = await service._detect_budget_threshold(uuid4(), Decimal("10.00"), location=None)

    assert created == 0
    assert invoked is False
