from datetime import date
from decimal import Decimal

from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.transaction_repo import TransactionRepo


class AnalyticsService:
    def __init__(self, repo: AnalyticsRepo):
        self.repo = repo

    async def summary(self, org_id, from_date: date, to_date: date):
        this_month = date(to_date.year, to_date.month, 1)
        snapshot = await self.repo.summary_snapshot(org_id, this_month)
        rev = snapshot["revenue_mtd"]
        exp = snapshot["expense_mtd"]
        burn = max(Decimal("0"), exp - rev)
        cash = snapshot["starting_cash"] + snapshot["revenue_total"] - snapshot["expense_total"]
        return {
            "cash_balance": cash,
            "revenue_mtd": rev,
            "expenses_mtd": exp,
            "net_profit_mtd": rev - exp,
            "burn_rate_monthly": burn,
            "alerts_count_open": int(snapshot["alerts_open"]),
        }

    async def runway(self, org_id, lookback_months: int, conservative: bool):
        months = await self.repo.monthly_lookback(org_id, lookback_months)
        if not months:
            burn = Decimal("0")
        else:
            burns = [max(Decimal("0"), m.expense_total - m.revenue_total) for m in months]
            if conservative and len(burns) >= 2:
                burn = sum(sorted(burns, reverse=True)[:2]) / Decimal("2")
            else:
                burn = sum(burns) / Decimal(str(len(burns)))
        cash = await self.repo.cash_balance(org_id)
        runway_days = 9999 if burn == 0 else int((cash / burn) * Decimal("30"))
        threshold = (
            await self.repo.runway_threshold_days(org_id)
            if hasattr(self.repo, "runway_threshold_days")
            else 60
        )
        return {
            "runway_days": runway_days,
            "monthly_burn": burn,
            "cash_balance": cash,
            "alert": runway_days < threshold,
        }

    async def recompute_monthly_aggregates(self, org_id) -> int:
        months = await self.repo.transaction_month_starts(org_id)
        tx_repo = TransactionRepo(self.repo.db)
        for month in months:
            await tx_repo.upsert_monthly_aggregate(org_id, month)
        return len(months)
