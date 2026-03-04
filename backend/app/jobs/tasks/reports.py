import asyncio
import uuid
from datetime import date, timedelta

import structlog
from celery import shared_task
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.models.job_state import JobState
from app.domain.models.membership import Membership
from app.domain.models.organization import Organization
from app.domain.models.user import User
from app.domain.repos.report_repo import ReportRepo
from app.domain.services.report_service import ReportService
from app.jobs.tasks.emails import send_email_task
from app.utils.time import utc_now

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def generate_weekly_report(
    self,
    org_id: str,
    week_start: str,
    created_by: str | None = None,
    correlation_id: str | None = None,
):
    return asyncio.run(_generate(org_id, week_start, created_by, correlation_id))


async def _generate(
    org_id: str,
    week_start: str,
    created_by: str | None = None,
    correlation_id: str | None = None,
):
    dedupe = f"report:{org_id}:{week_start}"
    org_uuid = uuid.UUID(org_id)
    async with SessionLocal() as db:
        state = await db.scalar(select(JobState).where(JobState.dedupe_key == dedupe))
        if not state:
            state = JobState(
                job_name="generate_weekly_report",
                dedupe_key=dedupe,
                status="RUNNING",
                payload={"org_id": org_id, "week_start": week_start, "correlation_id": correlation_id},
            )
            db.add(state)
        else:
            state.status = "RUNNING"
            state.updated_at = utc_now()

        svc = ReportService(ReportRepo(db))
        report = await svc.generate(
            org_uuid,
            date.fromisoformat(week_start),
            uuid.UUID(created_by) if created_by else None,
        )
        report_url = await svc.download_url(report)
        recipients = await db.execute(
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.org_id == org_uuid,
                Membership.role.in_(["OWNER", "EDITOR"]),
                User.is_active.is_(True),
            )
        )
        for email in recipients.scalars().all():
            send_email_task.delay(
                email,
                f"AI COO weekly report ({week_start})",
                f"Your weekly report is ready: {report_url}",
                correlation_id,
            )
        state.status = "DONE"
        state.result = {"report_id": str(report.id)}
        state.updated_at = utc_now()
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
        rows = await db.execute(select(Organization.id))
        org_ids = [str(r[0]) for r in rows.all()]
    for oid in org_ids:
        generate_weekly_report.delay(oid, week_start.isoformat(), None, None)
    logger.info("weekly_report_fanout", org_count=len(org_ids), week_start=week_start.isoformat())
    return len(org_ids)
