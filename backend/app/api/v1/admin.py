import uuid
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.core.auth_lockout import lockout_metrics
from app.core.config import get_settings
from app.core.slo_metrics import runtime_slo_snapshot
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.schedule_repo import ScheduleRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.deletion_repo import DeletionRepo
from app.domain.repos.dead_letter_repo import DeadLetterRepo
from app.domain.schemas.job import JobOut
from app.domain.schemas.operations import (
    BeatScheduleItemOut,
    DeadLetterEventOut,
    DeadLetterPageOut,
    OutboxEventOut,
    OutboxPageOut,
    RuntimeMetricsOut,
    RuntimeSLOOut,
    SystemStatusOut,
)
from app.domain.schemas.privacy import DeletionRequestItemOut, DeletionRequestListOut
from app.domain.services.job_dispatch_service import retry_job_task
from app.domain.services.notification_service import NotificationService
from app.domain.services.privacy_service import PrivacyService
from app.jobs.celery_app import celery_app
from app.jobs.tasks.admin import recompute_alerts, recompute_forecasts, recompute_monthly_aggregates, verify_report_objects
from app.jobs.tasks.outbox import process_outbox
from app.jobs.tasks.privacy import purge_deletion_requests
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
    if hasattr(db, "commit"):
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
                paused=bool(getattr(control, "paused", False)),
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


@router.get("/runtime-metrics", response_model=RuntimeMetricsOut)
async def runtime_metrics(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    job_repo = JobRepo(db)
    active_jobs = await job_repo.count_active(ctx.org_id)
    oldest_active = await job_repo.oldest_active_created_at(ctx.org_id)
    lag_seconds = int((datetime.now(timezone.utc) - oldest_active).total_seconds()) if oldest_active else 0
    dead_letter_open = await DeadLetterRepo(db).open_count(org_id=ctx.org_id)
    queue_lag_breach = lag_seconds > get_settings().runtime_queue_lag_threshold_seconds
    outbox_counts = await OutboxRepo(db).counts_by_status(org_id=ctx.org_id)
    db_active = await db.scalar(text("SELECT count(*)::int FROM pg_stat_activity WHERE state = 'active'"))
    auth_metrics = await lockout_metrics()
    return RuntimeMetricsOut(
        org_id=ctx.org_id,
        queue_depth_active=active_jobs,
        queue_lag_seconds=lag_seconds,
        queue_lag_breach=queue_lag_breach,
        outbox_pending=int((outbox_counts.get("PENDING") or 0) + (outbox_counts.get("RETRYING") or 0)),
        dead_letter_open=dead_letter_open,
        worker_health="degraded" if queue_lag_breach or dead_letter_open > 0 else "ok",
        db_active_connections=int(db_active or 0),
        auth_lockout_failures_total=int(auth_metrics.get("failures_total", 0)),
        auth_lockouts_total=int(auth_metrics.get("lockouts_total", 0)),
        auth_lockout_escalations_total=int(auth_metrics.get("escalations_total", 0)),
    )


@router.get("/runtime-slos", response_model=RuntimeSLOOut)
async def runtime_slos(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    settings = get_settings()
    snapshot = runtime_slo_snapshot(
        window_seconds=settings.runtime_slo_window_seconds,
        p95_threshold_ms=settings.runtime_slo_p95_ms,
        error_rate_threshold_pct=settings.runtime_slo_error_rate_pct,
        top_n=settings.runtime_slo_top_n,
    )
    return RuntimeSLOOut(org_id=ctx.org_id, **snapshot)


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
    if hasattr(db, "commit"):
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
    if hasattr(db, "commit"):
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
    elif name == "deletion-purge":
        result = purge_deletion_requests.apply_async(headers=headers)
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
    if hasattr(db, "commit"):
        await db.commit()
    return {"ok": True, "name": name, "task_id": result.id}


@router.get("/audit/export")
async def export_audit_logs(
    org_id: uuid.UUID = Query(...),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    rows = await AuditRepo(db).list_export_events(org_id=ctx.org_id, since=since, until=until, limit=20000)
    lines: list[str] = []
    for row in rows:
        payload = {
            "id": str(row.id),
            "created_at": row.created_at.isoformat(),
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "org_id": str(row.org_id) if row.org_id else None,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "metadata_json": row.metadata_json,
        }
        lines.append(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    checksum = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    headers = {
        "Content-Disposition": f'attachment; filename="audit-export-{org_id}.ndjson"',
        "X-Audit-Checksum-SHA256": checksum,
        "X-Audit-Event-Count": str(len(lines)),
    }
    return StreamingResponse(iter([("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")]), media_type="application/x-ndjson", headers=headers)


@router.post("/security/rotate-pii")
async def rotate_org_pii(
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    out = await PrivacyService(db, AuditRepo(db), DeletionRepo(db)).rotate_org_pii(actor_user_id=user.id, org_id=org_id)
    await db.commit()
    return {"ok": True, **out}


@router.get("/deletion-requests", response_model=DeletionRequestListOut)
async def list_deletion_requests(
    org_id: uuid.UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    rows = await PrivacyService(db, AuditRepo(db), DeletionRepo(db)).list_org_deletion_requests(
        actor_user_id=user.id,
        org_id=ctx.org_id,
        limit=limit,
    )
    return DeletionRequestListOut(items=[DeletionRequestItemOut.model_validate(row) for row in rows])


@router.get("/dead-letter", response_model=DeadLetterPageOut)
async def list_dead_letter(
    org_id: uuid.UUID = Query(...),
    status: str | None = None,
    source_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = DeadLetterRepo(db)
    items, total = await repo.list_events(
        org_id=ctx.org_id,
        status=status,
        source_type=source_type,
        page=page,
        page_size=page_size,
    )
    return DeadLetterPageOut(
        items=[DeadLetterEventOut.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        counts_by_status=await repo.counts_by_status(org_id=ctx.org_id),
    )


@router.post("/dead-letter/{dead_letter_id}/replay")
async def replay_dead_letter(
    dead_letter_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = DeadLetterRepo(db)
    item = await repo.by_id(dead_letter_id)
    if not item or item.org_id != ctx.org_id:
        return {"ok": False, "detail": "Dead-letter event not found"}

    replay_ref: str | None = None
    if item.source_type == "OUTBOX":
        source_id = item.source_id
        if not source_id:
            return {"ok": False, "detail": "Dead-letter event has no outbox source_id"}
        outbox = await OutboxRepo(db).by_id(source_id)
        if not outbox or outbox.org_id != ctx.org_id:
            return {"ok": False, "detail": "Outbox source not found"}
        await OutboxRepo(db).requeue(outbox, reset_attempts=True)
        replay_ref = str(outbox.id)
    elif item.source_type == "JOB":
        source_id = item.source_id
        if not source_id:
            return {"ok": False, "detail": "Dead-letter event has no job source_id"}
        job = await JobRepo(db).by_id(source_id)
        if not job or job.org_id != ctx.org_id:
            return {"ok": False, "detail": "Job source not found"}
        result = retry_job_task(job)
        if result is None:
            return {"ok": False, "detail": "Unsupported job replay"}
        replay_ref = str(result.id)
    else:
        return {"ok": False, "detail": f"Unsupported source_type {item.source_type}"}

    await repo.mark_replayed(item, metadata_json={"replayed_by": str(user.id), "replay_ref": replay_ref})
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Dead-letter replay dispatched",
        message=f"{item.source_type}:{item.source_name} replayed from dead-letter queue.",
        link="/app/activity",
        metadata_json={"dead_letter_id": str(item.id), "replay_ref": replay_ref},
    )
    if hasattr(db, "commit"):
        await db.commit()
    return {"ok": True, "id": str(item.id), "status": item.status, "replay_ref": replay_ref}


@router.post("/dead-letter/{dead_letter_id}/dismiss")
async def dismiss_dead_letter(
    dead_letter_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    reason: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    repo = DeadLetterRepo(db)
    item = await repo.by_id(dead_letter_id)
    if not item or item.org_id != ctx.org_id:
        return {"ok": False, "detail": "Dead-letter event not found"}
    await repo.mark_dismissed(item, reason=reason)
    await _notify(
        db,
        org_id=ctx.org_id,
        category="OPS",
        title="Dead-letter event dismissed",
        message=f"{item.source_type}:{item.source_name} dismissed by owner.",
        link="/app/activity",
        metadata_json={"dead_letter_id": str(item.id), "reason": reason},
    )
    if hasattr(db, "commit"):
        await db.commit()
    return {"ok": True, "id": str(item.id), "status": item.status}
