import uuid
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.idempotency_repo import IdempotencyRepo
from app.domain.repos.job_repo import JobRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.repos.plan_repo import PlanRepo
from app.domain.repos.report_repo import ReportRepo
from app.domain.schemas.reports import ReportGenerateOut, ReportItem, ReportsOut
from app.domain.services.idempotency_service import IdempotencyService
from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService
from app.domain.services.report_service import ReportService
from app.domain.services.usage_service import METRIC_REPORTS, UsageService
from app.jobs.tasks.reports import generate_weekly_report
from app.utils.idempotency_request import request_hash

router = APIRouter()


@router.get("", response_model=ReportsOut)
async def list_reports(
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    try:
        await LocationService(LocationRepo(db)).ensure_org_location(
            org_id=org_id,
            location_id=location_id,
            require_active=False,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rows = await ReportService(ReportRepo(db)).list_reports(org_id, location_id=location_id)
    return ReportsOut(
        items=[
            ReportItem(
                id=r.id,
                location_id=r.location_id,
                week_start=r.week_start,
                week_end=r.week_end,
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.post("/generate", response_model=ReportGenerateOut)
async def generate(
    request: Request,
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    week_start: date = Query(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    try:
        await LocationService(LocationRepo(db)).ensure_org_location(
            org_id=org_id,
            location_id=location_id,
            require_active=False,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    idem_service = IdempotencyService(IdempotencyRepo(db))
    idem_hash = request_hash({"org_id": org_id, "location_id": location_id, "week_start": week_start})
    replay = await idem_service.get_replay(
        org_id=org_id,
        user_id=user.id,
        endpoint="POST /api/v1/reports/generate",
        idempotency_key=idempotency_key,
        request_hash=idem_hash,
    )
    if replay:
        return JSONResponse(status_code=replay.status_code, content=replay.response_json)
    dedupe_key = f"report:{org_id}:{location_id or 'global'}:{week_start.isoformat()}"
    repo = ReportRepo(db)
    existing_report = await repo.get_by_week(org_id, week_start, location_id=location_id)
    if existing_report:
        # Fast path for idempotent reuse: avoid extra queries/writes in churn-heavy traffic.
        response_body = ReportGenerateOut(
            report_id=existing_report.id,
            job_id=f"reused-{existing_report.id}",
            status="SUCCEEDED",
        ).model_dump(mode="json")
        await idem_service.store_response(
            org_id=org_id,
            user_id=user.id,
            endpoint="POST /api/v1/reports/generate",
            idempotency_key=idempotency_key,
            request_hash=idem_hash,
            status_code=200,
            response_json=response_body,
        )
        return response_body

    job_repo = JobRepo(db)
    existing_job = await job_repo.by_dedupe_key(dedupe_key, org_id)
    if existing_job and existing_job.status in {"PENDING", "RUNNING", "RETRYING"}:
        response_body = ReportGenerateOut(
            report_id=(uuid.UUID(existing_job.result["report_id"]) if existing_job.result and existing_job.result.get("report_id") else None),
            job_id=existing_job.task_id,
            status=existing_job.status,
        ).model_dump(mode="json")
        await idem_service.store_response(
            org_id=org_id,
            user_id=user.id,
            endpoint="POST /api/v1/reports/generate",
            idempotency_key=idempotency_key,
            request_hash=idem_hash,
            status_code=200,
            response_json=response_body,
        )
        await db.commit()
        return response_body

    await UsageService(PlanRepo(db)).consume(org_id, METRIC_REPORTS, delta=1)
    task = generate_weekly_report.apply_async(
        args=[str(org_id), week_start.isoformat(), str(user.id), str(user.id), str(location_id) if location_id else None],
    )
    task_id = str(task.id)
    await job_repo.upsert_pending(
        task_id=task_id,
        task_name="generate_weekly_report",
        dedupe_key=dedupe_key,
        payload={
            "org_id": str(org_id),
            "location_id": str(location_id) if location_id else None,
            "week_start": week_start.isoformat(),
            "created_by": str(user.id),
        },
        org_id=org_id,
        request_id=getattr(request.state, "request_id", None),
        correlation_id=str(user.id),
    )
    await AuditRepo(db).log(
        user.id,
        org_id,
        "report.generate.enqueue",
        "job_state",
        task_id,
        {"week_start": week_start.isoformat(), "job_id": task_id},
    )
    response_body = ReportGenerateOut(report_id=None, job_id=task_id, status="PENDING").model_dump(mode="json")
    await idem_service.store_response(
        org_id=org_id,
        user_id=user.id,
        endpoint="POST /api/v1/reports/generate",
        idempotency_key=idempotency_key,
        request_hash=idem_hash,
        status_code=200,
        response_json=response_body,
    )
    await db.commit()
    return response_body


@router.get("/{report_id}/download")
async def download(
    report_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    location_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    try:
        await LocationService(LocationRepo(db)).ensure_org_location(
            org_id=org_id,
            location_id=location_id,
            require_active=False,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repo = ReportRepo(db)
    report = await repo.get(report_id, org_id, location_id=location_id)
    if not report:
        return {"url": None}
    url = await ReportService(repo).download_url(report)
    return {"url": url}
