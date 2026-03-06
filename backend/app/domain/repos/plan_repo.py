import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.organization_plan import OrganizationPlan
from app.domain.models.usage_meter import UsageMeter
from app.utils.time import utc_now


class PlanRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_plan(self, org_id: uuid.UUID) -> OrganizationPlan | None:
        q = await self.db.execute(select(OrganizationPlan).where(OrganizationPlan.org_id == org_id))
        return q.scalar_one_or_none()

    async def save_plan(self, plan: OrganizationPlan) -> OrganizationPlan:
        self.db.add(plan)
        await self.db.flush()
        return plan

    async def get_usage(self, org_id: uuid.UUID, metric: str, period_start: date) -> UsageMeter | None:
        q = await self.db.execute(
            select(UsageMeter).where(
                UsageMeter.org_id == org_id,
                UsageMeter.metric == metric,
                UsageMeter.period_start == period_start,
            )
        )
        return q.scalar_one_or_none()

    async def ensure_usage(self, org_id: uuid.UUID, metric: str, period_start: date, soft_limit: int) -> UsageMeter:
        usage = await self.get_usage(org_id, metric, period_start)
        if usage:
            if usage.soft_limit != soft_limit:
                usage.soft_limit = soft_limit
            return usage
        usage = UsageMeter(
            org_id=org_id,
            metric=metric,
            period_start=period_start,
            used_count=0,
            soft_limit=soft_limit,
            updated_at=utc_now(),
        )
        self.db.add(usage)
        await self.db.flush()
        return usage

    async def increment_usage(self, usage: UsageMeter, delta: int) -> UsageMeter:
        usage.used_count += delta
        usage.updated_at = utc_now()
        await self.db.flush()
        return usage
