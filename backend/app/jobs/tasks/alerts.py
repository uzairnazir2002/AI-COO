import uuid

import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.services.alerts_service import AlertsService
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def recalc_alerts(self, org_id: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="recalc_alerts",
        dedupe_key=f"alerts:{org_id}",
        payload={"org_id": org_id},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _recalc(org_id, correlation_id),
        result_payload_builder=lambda created: {"created_alerts": created},
    )


async def _recalc(org_id: str, correlation_id: str | None = None):
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        created = await AlertsService(db, AlertRepo(db), AuditRepo(db)).detect_and_create(org_uuid)
        await db.commit()
    logger.info(
        "alerts_recalc_done",
        org_id=org_id,
        correlation_id=correlation_id,
        created_alerts=created,
    )
    return created
