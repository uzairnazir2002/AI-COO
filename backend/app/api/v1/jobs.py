import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.schemas.job import JobCommandResult, JobOut, JobPageOut
from app.domain.services.job_dispatch_service import retry_job_task
from app.domain.services.notification_service import NotificationService
from app.jobs.celery_app import celery_app

router = APIRouter()
# Backward-compatible alias used by tests and internal monkeypatching.
_retry_task = retry_job_task


@router.get("", response_model=JobPageOut)
async def list_jobs(
    org_id: uuid.UUID = Query(...),
    status: str | None = None,
    task_name: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = JobRepo(db)
    items, total = await repo.list_jobs(
        org_id=ctx.org_id,
        status=status,
        task_name=task_name,
        since=since,
        until=until,
        page=page,
        page_size=page_size,
    )

    redacted = []
    for item in items:
        out = JobOut.model_validate(item)
        if ctx.role == "VIEWER":
            out.last_error = None
            out.traceback_summary = None
        redacted.append(out)

    return JobPageOut(items=redacted, page=page, page_size=page_size, total=total)


@router.post("/{job_id}/cancel", response_model=JobCommandResult)
async def cancel_job(
    job_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = JobRepo(db)
    job = await repo.by_id(job_id)
    if not job or job.org_id != ctx.org_id:
        return JobCommandResult(ok=False, job_id=str(job_id), status="NOT_FOUND")
    celery_app.control.revoke(job.task_id, terminate=True)
    await repo.mark_cancelled(job.task_id, error="Cancelled by operator")
    await NotificationService(NotificationRepo(db)).create_org_notification(
        org_id=ctx.org_id,
        category="OPS",
        title="Job cancelled",
        message=f"{job.task_name} was cancelled.",
        link="/app/activity",
        metadata_json={"task_id": job.task_id},
    )
    await db.commit()
    return JobCommandResult(ok=True, job_id=str(job.id), status="CANCELLED")


@router.post("/{job_id}/retry", response_model=JobCommandResult)
async def retry_job(
    job_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = JobRepo(db)
    job = await repo.by_id(job_id)
    if not job or job.org_id != ctx.org_id:
        return JobCommandResult(ok=False, job_id=str(job_id), status="NOT_FOUND")
    result = _retry_task(job)
    if result is None:
        return JobCommandResult(ok=False, job_id=str(job.id), status="UNSUPPORTED")
    await NotificationService(NotificationRepo(db)).create_org_notification(
        org_id=ctx.org_id,
        category="OPS",
        title="Job retried",
        message=f"{job.task_name} was re-queued.",
        link="/app/activity",
        metadata_json={"old_task_id": job.task_id, "new_task_id": result.id},
    )
    await db.commit()
    return JobCommandResult(ok=True, job_id=str(job.id), status="REQUEUED", new_task_id=result.id)
