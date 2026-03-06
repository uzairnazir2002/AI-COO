import traceback
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.plan_repo import PlanRepo
from app.domain.repos.report_repo import ReportRepo
from app.domain.schemas.reports import ReportGenerateOut, ReportItem, ReportsOut
from app.domain.services.report_service import ReportService
from app.domain.services.usage_service import METRIC_REPORTS, UsageService

router = APIRouter()


@router.get("", response_model=ReportsOut)
async def list_reports(org_id: uuid.UUID = Query(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await ReportService(ReportRepo(db)).list_reports(org_id)
    return ReportsOut(items=[ReportItem(id=r.id, week_start=r.week_start, week_end=r.week_end, created_at=r.created_at) for r in rows])


@router.post("/generate", response_model=ReportGenerateOut)
async def generate(
    request: Request,
    org_id: uuid.UUID = Query(...),
    week_start: date = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    task_id = str(uuid.uuid4())
    job_repo = JobRepo(db)
    await job_repo.upsert_running(
        task_id=task_id,
        task_name="generate_weekly_report",
        dedupe_key=f"report:{org_id}:{week_start.isoformat()}",
        payload={"org_id": str(org_id), "week_start": week_start.isoformat(), "created_by": str(user.id)},
        org_id=org_id,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=str(user.id),
    )
    try:
        await UsageService(PlanRepo(db)).consume(org_id, METRIC_REPORTS, delta=1)
        report = await ReportService(ReportRepo(db)).generate(org_id, week_start, user.id)
        await job_repo.mark_succeeded(task_id, {"report_id": str(report.id)})
    except Exception as exc:
        await job_repo.mark_failed(
            task_id,
            retry_count=0,
            error=str(exc),
            traceback_summary="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[:2000],
        )
        await db.commit()
        raise

    await AuditRepo(db).log(
        user.id,
        org_id,
        "report.generate",
        "report",
        str(report.id),
        {"week_start": week_start.isoformat(), "job_id": task_id},
    )
    await db.commit()
    return ReportGenerateOut(report_id=report.id, job_id=task_id)


@router.get("/{report_id}/download")
async def download(
    report_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    repo = ReportRepo(db)
    report = await repo.get(report_id, org_id)
    if not report:
        return {"url": None}
    url = await ReportService(repo).download_url(report)
    return {"url": url}
