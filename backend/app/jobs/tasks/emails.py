import asyncio

import structlog
from celery import shared_task
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.models.job_state import JobState
from app.infra.email import send_email
from app.utils.time import utc_now

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def send_email_task(self, to: str, subject: str, body: str, correlation_id: str | None = None):
    return asyncio.run(_send(to, subject, body, correlation_id))


async def _send(to: str, subject: str, body: str, correlation_id: str | None = None):
    dedupe = f"email:{to}:{subject}"
    async with SessionLocal() as db:
        state = await db.scalar(select(JobState).where(JobState.dedupe_key == dedupe))
        if not state:
            state = JobState(
                job_name="send_email",
                dedupe_key=dedupe,
                status="RUNNING",
                payload={"to": to, "subject": subject, "correlation_id": correlation_id},
            )
            db.add(state)
        send_email(to, subject, body)
        state.status = "DONE"
        state.updated_at = utc_now()
        state.result = {"sent": True}
        await db.commit()
    logger.info("email_sent", to=to, subject=subject, correlation_id=correlation_id)
    return True
