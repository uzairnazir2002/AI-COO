from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.schemas.organization import OrgSettingsUpdateIn


@pytest.mark.parametrize(
    ("payload", "field_name"),
    [
        ({"starting_cash": Decimal("-1")}, "starting_cash"),
        ({"runway_alert_threshold_days": 0}, "runway_alert_threshold_days"),
        ({"runway_alert_threshold_days": 3651}, "runway_alert_threshold_days"),
        ({"vendor_concentration_threshold_pct": Decimal("0.5")}, "vendor_concentration_threshold_pct"),
        ({"vendor_concentration_threshold_pct": Decimal("101")}, "vendor_concentration_threshold_pct"),
        ({"budget_variance_alert_threshold_pct": Decimal("0.5")}, "budget_variance_alert_threshold_pct"),
        ({"budget_variance_alert_threshold_pct": Decimal("1001")}, "budget_variance_alert_threshold_pct"),
        ({"misc_growth_multiplier": Decimal("1.0")}, "misc_growth_multiplier"),
        ({"misc_growth_multiplier": Decimal("10.1")}, "misc_growth_multiplier"),
        ({"anomaly_spike_multiplier": Decimal("0.9")}, "anomaly_spike_multiplier"),
        ({"anomaly_spike_multiplier": Decimal("11")}, "anomaly_spike_multiplier"),
        ({"owner_session_max_minutes": 4}, "owner_session_max_minutes"),
        ({"owner_session_max_minutes": 1441}, "owner_session_max_minutes"),
        ({"sensitive_action_reauth_minutes": 0}, "sensitive_action_reauth_minutes"),
        ({"sensitive_action_reauth_minutes": 5000}, "sensitive_action_reauth_minutes"),
    ],
)
def test_org_settings_validation_rejects_invalid_ranges(payload, field_name):
    with pytest.raises(ValidationError) as exc:
        OrgSettingsUpdateIn(**payload)
    assert field_name in str(exc.value)
