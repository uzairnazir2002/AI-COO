import uuid

import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.forecast_repo import ForecastRepo
from app.domain.services.forecast_service import ForecastService
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def recalc_forecasts(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recalc_forecasts",
        dedupe_key=f"forecast:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recalc(org_id, correlation_id),
        result_payload_builder=lambda count: {"rows": count},
    )


async def _recalc(org_id: str, correlation_id: str | None = None):
    async with SessionLocal() as db:
        svc = ForecastService(ForecastRepo(db), AnalyticsRepo(db))
        rows = await svc.ensure_forecasts(uuid.UUID(org_id), 6)
        await db.commit()
        count = len(rows)
    logger.info("forecast_recalc_done", org_id=org_id, correlation_id=correlation_id, rows=count)
    return count
