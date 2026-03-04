import asyncio
import uuid

import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.services.alerts_service import AlertsService

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def recalc_alerts(self, org_id: str, correlation_id: str | None = None):
    return asyncio.run(_recalc(org_id, correlation_id))


async def _recalc(org_id: str, correlation_id: str | None = None):
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        created = await AlertsService(db, AlertRepo(db)).detect_and_create(org_uuid)
        await db.commit()
    logger.info(
        "alerts_recalc_done",
        org_id=org_id,
        correlation_id=correlation_id,
        created_alerts=created,
    )
    return created
