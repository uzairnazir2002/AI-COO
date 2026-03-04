from decimal import Decimal

import pytest

from app.domain.services.analytics_service import AnalyticsService


class M:
    def __init__(self, rev, exp):
        self.revenue_total = Decimal(rev)
        self.expense_total = Decimal(exp)


class Repo:
    async def monthly_lookback(self, org_id, months):
        return [M("1000", "1600"), M("1000", "2000"), M("1200", "1500")]

    async def cash_balance(self, org_id):
        return Decimal("6000")


@pytest.mark.asyncio
async def test_runway_conservative():
    out = await AnalyticsService(Repo()).runway("org", 3, True)
    assert out["monthly_burn"] == Decimal("800")
    assert out["runway_days"] == 225
