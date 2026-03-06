import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.schedule_repo import ScheduleRepo
from app.domain.services.notification_service import NotificationService
from app.infra.email import send_email
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def process_outbox(self, batch_size: int = 100, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=None,
        task_name="process_outbox",
        dedupe_key=f"outbox:{batch_size}",
        payload={"batch_size": batch_size},
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _process(batch_size, correlation_id),
        result_payload_builder=lambda count: {"processed": count},
    )


async def _process(batch_size: int, correlation_id: str | None = None) -> int:
    processed = 0
    async with SessionLocal() as db:
        control = await ScheduleRepo(db).get("outbox-consumer")
        if control and control.paused:
            return 0
        repo = OutboxRepo(db)
        events = await repo.claim_pending(limit=batch_size)
        await db.commit()

        for event in events:
            try:
                if event.event_type == "email.send":
                    payload = event.payload or {}
                    send_email(
                        payload["to"],
                        payload["subject"],
                        payload["body"],
                    )
                await repo.mark_sent(event)
            except Exception as exc:
                await repo.mark_retry_or_failed(event, str(exc))
                if event.org_id:
                    await NotificationService(NotificationRepo(db)).create_org_notification(
                        org_id=event.org_id,
                        category="OPS",
                        title="Outbox delivery failed",
                        message=f"{event.event_type} failed and will retry.",
                        link="/app/activity",
                        metadata_json={"event_id": str(event.id), "error": str(exc)},
                    )
            finally:
                await db.commit()
                processed += 1

    logger.info("outbox_processed", processed=processed, correlation_id=correlation_id)
    return processed
