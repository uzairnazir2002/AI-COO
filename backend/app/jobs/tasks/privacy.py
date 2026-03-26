import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.deletion_repo import DeletionRepo
from app.domain.services.privacy_service import PrivacyService
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def purge_deletion_requests(self, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=None,
        task_name="purge_deletion_requests",
        dedupe_key="purge-deletion-requests",
        payload={},
        correlation_id=correlation_id,
        max_retries=2,
        runner=_purge_deletions,
        result_payload_builder=lambda result: result,
    )


async def _purge_deletions() -> dict:
    async with SessionLocal() as db:
        svc = PrivacyService(db, AuditRepo(db), DeletionRepo(db))
        out = await svc.process_due_deletions(limit=200)
        await db.commit()
    logger.info("purge_deletion_requests_done", **out)
    return out
