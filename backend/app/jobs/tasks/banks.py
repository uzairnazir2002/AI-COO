import uuid

import structlog
from celery import shared_task

from app.db.session import SessionLocal
from app.domain.models.bank_connection import BankConnection
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.bank_repo import BankRepo
from app.domain.repos.schedule_repo import ScheduleRepo
from app.domain.repos.transaction_repo import TransactionRepo
from app.domain.services.bank_integration_service import BankIntegrationService
from app.jobs.task_tracking import run_tracked_task
from sqlalchemy import select

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def sync_bank_connection(
    self,
    org_id: str,
    connection_id: str,
    actor_user_id: str | None = None,
    correlation_id: str | None = None,
):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="sync_bank_connection",
        dedupe_key=f"bank-sync:{org_id}:{connection_id}",
        payload={
            "org_id": org_id,
            "connection_id": connection_id,
            "actor_user_id": actor_user_id,
        },
        correlation_id=correlation_id,
        max_retries=3,
        runner=lambda: _sync(org_id, connection_id, actor_user_id),
        result_payload_builder=lambda result: result,
    )


async def _sync(org_id: str, connection_id: str, actor_user_id: str | None = None) -> dict:
    org_uuid = uuid.UUID(org_id)
    conn_uuid = uuid.UUID(connection_id)
    if not actor_user_id:
        raise ValueError("actor_user_id is required")
    actor_uuid = uuid.UUID(actor_user_id)
    async with SessionLocal() as db:
        service = BankIntegrationService(BankRepo(db), AuditRepo(db), TransactionRepo(db))
        run, stats = await service.sync_connection(
            org_id=org_uuid,
            actor_user_id=actor_uuid,
            connection_id=conn_uuid,
        )
        await db.commit()
    payload = {
        "sync_run_id": str(run.id),
        "fetched_count": stats.fetched_count,
        "inserted_count": stats.inserted_count,
        "duplicate_count": stats.duplicate_count,
        "cursor_after": stats.cursor_after,
    }
    logger.info("bank_sync_done", org_id=org_id, connection_id=connection_id, **payload)
    return payload


@shared_task(bind=True)
def sync_all_active_bank_connections(self, correlation_id: str | None = None):
    return run_tracked_task(
        self,
        org_id=None,
        task_name="sync_all_active_bank_connections",
        dedupe_key="bank-sync:all-active",
        payload={},
        correlation_id=correlation_id,
        max_retries=1,
        runner=_sync_all_active,
        result_payload_builder=lambda result: result,
    )


async def _sync_all_active() -> dict:
    enqueued = 0
    skipped_without_actor = 0
    async with SessionLocal() as db:
        control = await ScheduleRepo(db).get("bank-sync")
        if control and control.paused:
            return {"enqueued": 0, "paused": True, "skipped_without_actor": 0}
        rows = await db.execute(
            select(BankConnection.id, BankConnection.org_id, BankConnection.connected_by_user_id)
            .where(BankConnection.status == "ACTIVE")
            .order_by(BankConnection.created_at.asc())
        )
        for connection_id, org_id, actor_user_id in rows.all():
            if actor_user_id is None:
                skipped_without_actor += 1
                continue
            sync_bank_connection.delay(str(org_id), str(connection_id), str(actor_user_id), "bank-sync-beat")
            enqueued += 1
    logger.info("bank_sync_fanout_done", enqueued=enqueued, skipped_without_actor=skipped_without_actor)
    return {"enqueued": enqueued, "paused": False, "skipped_without_actor": skipped_without_actor}
