from decimal import Decimal

import pytest


@pytest.fixture
def sample_monthly_aggregates():
    class M:
        def __init__(self, rev, exp):
            self.revenue_total = Decimal(rev)
            self.expense_total = Decimal(exp)

    return [M("1000", "1400"), M("1200", "1800"), M("900", "1500")]


@pytest.fixture
def sample_metrics():
    return {
        "kpis": {"revenue_mtd": "1200", "expenses_mtd": "900"},
        "alerts": [{"title": "Runway low", "severity": "HIGH"}],
    }
