import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_announcement_repo import WorkforceAnnouncementRepo
from app.domain.services.workforce_announcement_service import build_workforce_announcement_service
from app.jobs.task_tracking import run_tracked_task
from app.utils.time import utc_now

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def publish_due_workforce_announcements(self, batch_size: int = 50, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=None,
        task_name="publish_due_workforce_announcements",
        dedupe_key=f"wf_ann_sched:{batch_size}",
        payload={"batch_size": batch_size},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _run_publish_due(batch_size, correlation_id),
        result_payload_builder=lambda n: {"published": n},
    )


async def _run_publish_due(batch_size: int, correlation_id: str | None) -> int:
    now = utc_now()
    due = []
    async with SessionLocal() as db:
        due = await WorkforceAnnouncementRepo(db).list_due_scheduled(now=now, limit=batch_size)

    count = 0
    for row in due:
        async with SessionLocal() as db:
            try:
                svc = build_workforce_announcement_service(db)
                published = await svc.publish(org_id=row.org_id, announcement_id=row.id)
                await AuditRepo(db).log(
                    published.created_by_user_id,
                    row.org_id,
                    "workforce.announcement.publish.scheduled",
                    "workforce_announcement",
                    str(published.id),
                    {},
                )
                await db.commit()
                count += 1
            except ValueError as exc:
                await db.rollback()
                if "Only draft announcements can be published" in str(exc):
                    logger.info("scheduled_announcement_skip_not_draft", announcement_id=str(row.id))
                    continue
                logger.warning("scheduled_announcement_publish_value_error", error=str(exc), announcement_id=str(row.id))
            except Exception:
                await db.rollback()
                logger.exception("scheduled_announcement_publish_failed", announcement_id=str(row.id))

    logger.info("workforce_ann_scheduled_published", count=count, correlation_id=correlation_id)
    return count
