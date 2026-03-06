import asyncio
import uuid
from datetime import date, timedelta

import structlog
from celery import shared_task
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.models.organization import Organization
from app.domain.repos.report_repo import ReportRepo
from app.domain.repos.schedule_repo import ScheduleRepo
from app.domain.services.report_service import ReportService
from app.jobs.task_tracking import run_tracked_task

logger = structlog.get_logger(__name__)


@shared_task(bind=True)
def generate_weekly_report(
    self,
    org_id: str,
    week_start: str,
    created_by: str | None = None,
    correlation_id: str | None = None,
):
    return run_tracked_task(
        self,
        org_id=org_id,
        task_name="generate_weekly_report",
        dedupe_key=f"report:{org_id}:{week_start}",
        payload={"org_id": org_id, "week_start": week_start, "created_by": created_by},
        correlation_id=correlation_id,
        max_retries=5,
        runner=lambda: _generate(org_id, week_start, created_by, correlation_id),
        result_payload_builder=lambda report_id: {"report_id": report_id},
    )


async def _generate(
    org_id: str,
    week_start: str,
    created_by: str | None = None,
    correlation_id: str | None = None,
):
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        svc = ReportService(ReportRepo(db))
        report = await svc.generate(
            org_uuid,
            date.fromisoformat(week_start),
            uuid.UUID(created_by) if created_by else None,
        )
        await db.commit()
    logger.info(
        "weekly_report_generated",
        org_id=org_id,
        week_start=week_start,
        correlation_id=correlation_id,
        report_id=str(report.id),
    )
    return str(report.id)


@shared_task(bind=True)
def generate_all_org_reports(self):
    return asyncio.run(_for_all())


async def _for_all():
    today = date.today()
    week_start = today - timedelta(days=today.weekday() + 7)
    async with SessionLocal() as db:
        control = await ScheduleRepo(db).get("weekly-reports")
        if control and control.paused:
            return 0
        rows = await db.execute(select(Organization.id))
        org_ids = [str(r[0]) for r in rows.all()]
    for oid in org_ids:
        generate_weekly_report.delay(oid, week_start.isoformat(), None, None)
    logger.info("weekly_report_fanout", org_count=len(org_ids), week_start=week_start.isoformat())
    return len(org_ids)
