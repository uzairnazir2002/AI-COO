from decimal import Decimal

from app.domain.services.alerts_service import AlertsService


def test_mad_score_detects_spike():
    history = [Decimal("100"), Decimal("105"), Decimal("110"), Decimal("98"), Decimal("102")]
    latest = Decimal("300")
    score = AlertsService._robust_mad_score(history, latest)
    assert score is not None
    assert score > Decimal("3.5")


def test_z_score_detects_spike_when_variance_exists():
    history = [Decimal("10"), Decimal("11"), Decimal("9"), Decimal("12"), Decimal("10")]
    latest = Decimal("30")
    score = AlertsService._z_score(history, latest)
    assert score is not None
    assert score > Decimal("3.0")
