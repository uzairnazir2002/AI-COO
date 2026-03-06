import uuid
from dataclasses import dataclass
from datetime import date

from app.domain.models.organization_plan import OrganizationPlan
from app.domain.repos.plan_repo import PlanRepo
from app.domain.services.errors import LimitExceededError
from app.utils.time import month_start


METRIC_TRANSACTIONS = "transactions"
METRIC_REPORTS = "reports"
METRIC_AI_SUMMARIES = "ai_summaries"


@dataclass
class UsageSnapshot:
    metric: str
    used: int
    limit: int
    period_start: date


class UsageService:
    def __init__(self, repo: PlanRepo):
        self.repo = repo

    async def ensure_plan(self, org_id: uuid.UUID) -> OrganizationPlan:
        plan = await self.repo.get_plan(org_id)
        if plan:
            return plan
        plan = OrganizationPlan(
            org_id=org_id,
            code="FREE",
            transaction_limit_monthly=10000,
            report_limit_monthly=20,
            ai_summary_limit_monthly=500,
        )
        return await self.repo.save_plan(plan)

    async def consume(self, org_id: uuid.UUID, metric: str, delta: int = 1) -> UsageSnapshot:
        if delta <= 0:
            raise ValueError("delta must be > 0")
        plan = await self.ensure_plan(org_id)
        limit = self._limit_for(plan, metric)
        period = month_start(date.today())
        usage = await self.repo.ensure_usage(org_id, metric, period, limit)
        projected = usage.used_count + delta
        if projected > limit:
            raise LimitExceededError(
                f"Plan limit exceeded for {metric}: {usage.used_count}/{limit} used this month."
            )
        usage = await self.repo.increment_usage(usage, delta)
        return UsageSnapshot(metric=metric, used=usage.used_count, limit=limit, period_start=period)

    async def get_usage_overview(self, org_id: uuid.UUID) -> dict:
        plan = await self.ensure_plan(org_id)
        period = month_start(date.today())
        metrics = [
            METRIC_TRANSACTIONS,
            METRIC_REPORTS,
            METRIC_AI_SUMMARIES,
        ]
        out = {}
        for metric in metrics:
            limit = self._limit_for(plan, metric)
            usage = await self.repo.ensure_usage(org_id, metric, period, limit)
            out[metric] = {"used": usage.used_count, "limit": limit}
        return {
            "plan_code": plan.code,
            "period_start": period,
            "metrics": out,
        }

    @staticmethod
    def _limit_for(plan: OrganizationPlan, metric: str) -> int:
        if metric == METRIC_TRANSACTIONS:
            return plan.transaction_limit_monthly
        if metric == METRIC_REPORTS:
            return plan.report_limit_monthly
        if metric == METRIC_AI_SUMMARIES:
            return plan.ai_summary_limit_monthly
        raise ValueError(f"Unsupported usage metric: {metric}")
