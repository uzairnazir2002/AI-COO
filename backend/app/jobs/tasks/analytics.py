import uuid

import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.analytics_repo import AnalyticsRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.forecast_repo import ForecastRepo
from app.domain.services.alerts_service import AlertsService
from app.domain.services.forecast_service import ForecastService
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def recompute_org_analytics(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recompute_org_analytics",
        dedupe_key=f"analytics-recompute:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recompute(org_id, correlation_id),
        result_payload_builder=lambda result: result,
    )


async def _recompute(org_id: str, correlation_id: str | None = None) -> dict:
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        alerts_created = await AlertsService(db, AlertRepo(db), AuditRepo(db)).detect_and_create(org_uuid)
        forecast_rows = await ForecastService(ForecastRepo(db), AnalyticsRepo(db)).ensure_forecasts(org_uuid, 6)
        await db.commit()
    rows = len(forecast_rows)
    logger.info(
        "analytics_recompute_done",
        org_id=org_id,
        correlation_id=correlation_id,
        alerts_created=alerts_created,
        forecast_rows=rows,
    )
    return {"alerts_created": alerts_created, "forecast_rows": rows}
