import structlog
from celery import shared_task

from app.infra.email import send_email
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def send_email_task(self, to: str, subject: str, body: str, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=None,
        task_name="send_email",
        dedupe_key=f"email:{to}:{subject}",
        payload={"to": to, "subject": subject},
        correlation_id=correlation_id,
        max_retries=5,
        runner=lambda: _send(to, subject, body, correlation_id),
        result_payload_builder=lambda result: {"sent": result},
    )


async def _send(to: str, subject: str, body: str, correlation_id: str | None = None):
    send_email(to, subject, body)
    logger.info("email_sent", to=to, subject=subject, correlation_id=correlation_id)
    return True
