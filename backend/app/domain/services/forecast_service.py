from datetime import date, datetime
from decimal import Decimal

from app.domain.models.forecast import Forecast
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.forecast_repo import ForecastRepo


class ForecastService:
    def __init__(self, forecast_repo: ForecastRepo, analytics_repo: AnalyticsRepo):
        self.forecast_repo = forecast_repo
        self.analytics_repo = analytics_repo

    async def ensure_forecasts(self, org_id, months: int):
        existing = await self.forecast_repo.list_forecasts(org_id, months)
        if existing:
            return existing
        lookback = await self.analytics_repo.monthly_lookback(org_id, 6)
        avg_rev = sum((m.revenue_total for m in lookback), Decimal("0")) / Decimal(str(len(lookback) or 1))
        avg_exp = sum((m.expense_total for m in lookback), Decimal("0")) / Decimal(str(len(lookback) or 1))

        rows = []
        today = date.today()
        for i in range(1, months + 1):
            month = date(today.year + ((today.month + i - 1) // 12), ((today.month + i - 1) % 12) + 1, 1)
            for scenario, rm, em in [("BASE", Decimal("1.00"), Decimal("1.00")), ("HIGH", Decimal("1.10"), Decimal("0.95")), ("LOW", Decimal("0.90"), Decimal("1.10"))]:
                rev = (avg_rev * rm).quantize(Decimal("0.01"))
                exp = (avg_exp * em).quantize(Decimal("0.01"))
                f = Forecast(
                    org_id=org_id,
                    month=month,
                    scenario=scenario,
                    revenue_pred=rev,
                    expense_pred=exp,
                    confidence_low=(rev - exp * Decimal("0.1")).quantize(Decimal("0.01")),
                    confidence_high=(rev + exp * Decimal("0.1")).quantize(Decimal("0.01")),
                )
                await self.forecast_repo.save(f)
                rows.append(f)
        return rows

    async def override(self, org_id, month: date, scenario: str, revenue_override, expense_override):
        f = await self.forecast_repo.get_one(org_id, month, scenario)
        if not f:
            return False
        ov = f.overrides or {}
        if revenue_override is not None:
            f.revenue_pred = revenue_override
            ov["revenue_override"] = str(revenue_override)
        if expense_override is not None:
            f.expense_pred = expense_override
            ov["expense_override"] = str(expense_override)
        ov["updated_at"] = datetime.utcnow().isoformat()
        f.overrides = ov
        await self.forecast_repo.save(f)
        return True

    async def recompute(self, org_id, months: int = 6) -> int:
        await self.forecast_repo.delete_for_org(org_id)
        rows = await self.ensure_forecasts(org_id, months)
        return len(rows)
