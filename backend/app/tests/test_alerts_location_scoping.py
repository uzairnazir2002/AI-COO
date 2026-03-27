from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.services.alerts_service import AlertsService


@pytest.mark.asyncio
async def test_detect_and_create_runs_global_and_location_contexts(monkeypatch):
    org_id = uuid4()
    location = SimpleNamespace(id=uuid4(), name="Karachi HQ")
    service = AlertsService(db=SimpleNamespace(), repo=SimpleNamespace())  # type: ignore[arg-type]

    async def fake_scalar(_query):
        return SimpleNamespace(
            anomaly_spike_multiplier=Decimal("1.5"),
            vendor_concentration_threshold_pct=Decimal("50.00"),
            budget_variance_alert_threshold_pct=Decimal("10.00"),
            misc_growth_multiplier=Decimal("1.4"),
        )

    service.db.scalar = fake_scalar  # type: ignore[attr-defined]

    async def fake_contexts(_org_id):
        assert _org_id == org_id
        return [None, location]

    calls: list[tuple[str, str | None]] = []

    def make_detector(name):
        async def _detector(*_args, location=None, **_kwargs):
            calls.append((name, str(location.id) if location else None))
            return 1

        return _detector

    monkeypatch.setattr(service, "_detection_contexts", fake_contexts)
    monkeypatch.setattr(service, "_detect_anomaly", make_detector("anomaly"))
    monkeypatch.setattr(service, "_detect_vendor_concentration", make_detector("vendor"))
    monkeypatch.setattr(service, "_detect_budget_threshold", make_detector("budget"))
    monkeypatch.setattr(service, "_detect_misc_growth", make_detector("misc"))
    monkeypatch.setattr(service, "_detect_margin_decline", make_detector("margin"))
    monkeypatch.setattr(service, "_detect_subscription_creep", make_detector("subscription"))
    monkeypatch.setattr(service, "_detect_inventory_stockout_risk", make_detector("inventory"))

    created = await service.detect_and_create(org_id)

    assert created == 14
    assert ("anomaly", None) in calls
    assert ("anomaly", str(location.id)) in calls
