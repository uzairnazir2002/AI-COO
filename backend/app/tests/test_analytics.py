from datetime import date
from decimal import Decimal

import pytest

from app.domain.services.analytics_service import AnalyticsService


class Repo:
    async def summary_snapshot(self, org_id, month_start, **_kwargs):
        _ = (org_id, month_start)
        return {
            "starting_cash": Decimal("5200"),
            "revenue_total": Decimal("1000"),
            "expense_total": Decimal("1200"),
            "revenue_mtd": Decimal("1000"),
            "expense_mtd": Decimal("1200"),
            "alerts_open": 3,
        }

    async def cash_balance(self, org_id, **_kwargs):
        return Decimal("5000")

    async def alerts_open_count(self, org_id):
        return 3


@pytest.mark.asyncio
async def test_summary_calc():
    out = await AnalyticsService(Repo()).summary("org", date(2026, 3, 1), date(2026, 3, 3))
    assert out["net_profit_mtd"] == Decimal("-200")
    assert out["burn_rate_monthly"] == Decimal("200")
