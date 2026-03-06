import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.schedule_repo import ScheduleRepo
from app.domain.schemas.job import JobOut
from app.domain.schemas.operations import BeatScheduleItemOut, OutboxEventOut, OutboxPageOut, SystemStatusOut
from app.domain.services.notification_service import NotificationService
from app.jobs.celery_app import celery_app
from app.jobs.tasks.admin import recompute_alerts, recompute_forecasts, recompute_monthly_aggregates, verify_report_objects
from app.jobs.tasks.outbox import process_outbox
from app.jobs.tasks.reports import generate_all_org_reports

router = APIRouter()


async def _notify(db: AsyncSession, **kwargs) -> None:
    if not hasattr(db, "add"):
        return
    await NotificationService(NotificationRepo(db)).create_org_notification(**kwargs)


@router.post("/recompute")
async def recompute_all(
    request: Request,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    correlation_id = str(getattr(user, "id", ""))
    headers = {"x-request-id": getattr(request.state, "request_id", "")}

    agg_job = recompute_monthly_aggregates.apply_async(args=[str(ctx.org_id), correlation_id], headers=headers)
    forecast_job = recompute_forecasts.apply_async(args=[str(ctx.org_id), correlation_id], headers=headers)
    alerts_job = recompute_alerts.apply_async(args=[str(ctx.org_id), correlation_id], headers=headers)
    verify_job = verify_report_objects.apply_async(args=[str(ctx.org_id), correlation_id], headers=headers)

    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Full recompute queued",
        message="Monthly aggregates, forecasts, alerts, and report verification were queued.",
        link="/app/activity",
        metadata_json={
            "jobs": {
                "monthly_aggregates": agg_job.id,
                "forecasts": forecast_job.id,
                "alerts": alerts_job.id,
                "report_object_verify": verify_job.id,
            }
        },
    )
    await db.commit()

    return {
        "ok": True,
        "jobs": {
            "monthly_aggregates": agg_job.id,
            "forecasts": forecast_job.id,
            "alerts": alerts_job.id,
            "report_object_verify": verify_job.id,
        },
    }


@router.get("/outbox", response_model=OutboxPageOut)
async def list_outbox(
    org_id: uuid.UUID = Query(...),
    status: str | None = None,
    event_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = OutboxRepo(db)
    items, total = await repo.list_events(
        org_id=ctx.org_id,
        status=status,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    return OutboxPageOut(
        items=[OutboxEventOut.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        counts_by_status=await repo.counts_by_status(org_id=ctx.org_id),
    )


@router.post("/outbox/{event_id}/retry")
async def retry_outbox_event(
    event_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = OutboxRepo(db)
    event = await repo.by_id(event_id)
    if not event or event.org_id != ctx.org_id:
        return {"ok": False, "detail": "Outbox event not found"}
    await repo.requeue(event, reset_attempts=True)
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Outbox event re-queued",
        message=f"{getattr(event, 'event_type', 'Outbox event')} was queued for another delivery attempt.",
        link="/app/activity",
        metadata_json={"event_id": str(event.id)},
    )
    if hasattr(db, "commit"):
        await db.commit()
    return {"ok": True, "id": str(event.id), "status": event.status}


@router.get("/system-status", response_model=SystemStatusOut)
async def system_status(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    schedule_repo = ScheduleRepo(db)
    schedules = []
    for name, entry in (celery_app.conf.beat_schedule or {}).items():
        try:
            control = await schedule_repo.get(name)
        except AttributeError:
            control = None
        schedules.append(
            BeatScheduleItemOut(
                name=name,
                task=str(entry.get("task", "")),
                schedule=str(entry.get("schedule", "")),
                paused=bool(control.paused) if control else False,
            )
        )

    job_repo = JobRepo(db)
    system_jobs, total = await job_repo.list_system_jobs(page=1, page_size=10)
    outbox_counts = await OutboxRepo(db).counts_by_status(org_id=ctx.org_id)
    return SystemStatusOut(
        scheduler=schedules,
        system_jobs=[JobOut.model_validate(item) for item in system_jobs],
        system_job_total=total,
        org_outbox_counts=outbox_counts,
    )


@router.post("/schedules/{name}/pause")
async def pause_schedule(
    name: str,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    control = await ScheduleRepo(db).set_paused(name, True)
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Schedule paused",
        message=f"{name} will be skipped until resumed.",
        link="/app/activity",
        metadata_json={"schedule": name},
    )
    await db.commit()
    return {"ok": True, "name": control.name, "paused": control.paused}


@router.post("/schedules/{name}/resume")
async def resume_schedule(
    name: str,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    control = await ScheduleRepo(db).set_paused(name, False)
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Schedule resumed",
        message=f"{name} is active again.",
        link="/app/activity",
        metadata_json={"schedule": name},
    )
    await db.commit()
    return {"ok": True, "name": control.name, "paused": control.paused}


@router.post("/schedules/{name}/run")
async def run_schedule_now(
    name: str,
    request: Request,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    headers = {"x-request-id": getattr(request.state, "request_id", "")}
    if name == "weekly-reports":
        result = generate_all_org_reports.apply_async(headers=headers)
    elif name == "outbox-consumer":
        result = process_outbox.apply_async(headers=headers)
    else:
        return {"ok": False, "detail": "Unknown schedule"}
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Manual schedule run started",
        message=f"{name} was dispatched manually.",
        link="/app/activity",
        metadata_json={"schedule": name, "task_id": result.id},
    )
    await db.commit()
    return {"ok": True, "name": name, "task_id": result.id}
