from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.domain.schemas.organization import OrgSettingsUpdateIn


@pytest.mark.asyncio
async def test_update_settings_blocks_editor_from_security_fields(monkeypatch):
    from app.api.v1 import organizations as org_module

    body = OrgSettingsUpdateIn(owner_mfa_required=True)
    with pytest.raises(HTTPException) as exc:
        await org_module.update_settings(
            org_id=uuid4(),
            body=body,
            user=SimpleNamespace(id=uuid4()),
            _=object(),
            ctx=SimpleNamespace(role="EDITOR"),
            __=object(),
            db=object(),
        )
    assert exc.value.status_code == 403
    assert "Only owners can update security policy settings" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_update_settings_allows_editor_financial_fields(monkeypatch):
    from app.api.v1 import organizations as org_module

    class _FakeOrgService:
        def __init__(self, *_args, **_kwargs):
            pass

        async def update_settings(self, *_args, **_kwargs):
            return SimpleNamespace(
                starting_cash=Decimal("1000.00"),
                runway_alert_threshold_days=60,
                vendor_concentration_threshold_pct=Decimal("50.00"),
                budget_variance_alert_threshold_pct=Decimal("10.00"),
                misc_growth_multiplier=Decimal("1.40"),
                anomaly_spike_multiplier=Decimal("1.50"),
                owner_mfa_required=False,
                owner_session_max_minutes=120,
                sensitive_action_reauth_minutes=30,
            )

    class _FakeDb:
        async def commit(self):
            return None

    monkeypatch.setattr(org_module, "OrgService", _FakeOrgService)

    out = await org_module.update_settings(
        org_id=uuid4(),
        body=OrgSettingsUpdateIn(starting_cash=Decimal("1000.00")),
        user=SimpleNamespace(id=uuid4()),
        _=object(),
        ctx=SimpleNamespace(role="EDITOR"),
        __=object(),
        db=_FakeDb(),
    )

    assert str(out.starting_cash) == "1000.00"
    assert str(out.budget_variance_alert_threshold_pct) == "10.00"
    assert out.owner_mfa_required is False
