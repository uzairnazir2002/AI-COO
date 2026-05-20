import re
import uuid
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_sensitive_reauth, resolve_workforce_org_id_from_request
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_hr_repo import WorkforceHrRepo
from app.domain.schemas.workforce_hr import (
    WorkforceChecklistDoneIn,
    WorkforceChecklistItemCreateIn,
    WorkforceChecklistItemOut,
    WorkforceDocumentDeactivateIn,
    WorkforceDocumentOut,
    WorkforceDocumentUploadOut,
    WorkforcePolicyAckCreateIn,
    WorkforcePolicyAckOut,
    WorkforcePolicyCreateIn,
    WorkforcePolicyOut,
    WorkforcePolicyPublishIn,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.notification_service import NotificationService
from app.domain.services.workforce_hr_service import WorkforceHrService
from app.infra.s3 import ensure_bucket, s3_client

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


_DOC_UPLOAD_MAX_BYTES = 15 * 1024 * 1024
_DOC_UPLOAD_TYPES = frozenset({"application/pdf", "image/png", "image/jpeg", "text/plain"})
_SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_upload_filename(name: str | None) -> str:
    base = (name or "document").split("/")[-1].split("\\")[-1]
    cleaned = _SAFE_FILENAME.sub("_", base).strip("._") or "document"
    return cleaned[:180]


def _presigned_url(*, object_key: str) -> str:
    s3 = s3_client()
    settings = get_settings()
    ensure_bucket(s3)
    bucket = settings.minio_bucket
    url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": object_key}, ExpiresIn=7 * 24 * 3600)
    public_base = (settings.minio_public_base_url or "").strip()
    if not public_base:
        return url
    try:
        source = urlparse(url)
        target = urlparse(public_base)
        if not target.scheme or not target.netloc:
            return url
        return urlunparse((target.scheme, target.netloc, source.path, source.params, source.query, source.fragment))
    except Exception:
        return url


def _svc(db: AsyncSession) -> WorkforceHrService:
    return WorkforceHrService(hr_repo=WorkforceHrRepo(db), employee_repo=WorkforceEmployeeRepo(db))


async def _notify_workforce_event(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    title: str,
    message: str,
    link: str,
    metadata_json: dict | None = None,
) -> None:
    try:
        await NotificationService(NotificationRepo(db)).create_org_notification(
            org_id=org_id,
            category="WORKFORCE",
            title=title,
            message=message,
            link=link,
            metadata_json=metadata_json or {},
        )
    except Exception:
        # Best-effort: notification failures must not block HR admin workflows.
        return


# Policies
@router.get("/policies", response_model=list[WorkforcePolicyOut])
async def list_policies(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    rows = await _svc(db).list_policies(org_id=resolved_org_id, include_inactive=include_inactive, limit=limit)
    return [WorkforcePolicyOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/policies", response_model=WorkforcePolicyOut)
async def create_policy(
    request: Request,
    body: WorkforcePolicyCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_policy(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            code=body.code,
            title=body.title,
            body=body.body,
            requires_ack=body.requires_ack,
            publish_now=body.publish_now,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, resolved_org_id, "workforce.policy.create", "workforce_policy", str(row.id), {"code": row.code})
    await db.commit()
    return WorkforcePolicyOut.model_validate(row, from_attributes=True)


@router.post("/policies/{policy_id}/publish", response_model=WorkforcePolicyOut)
async def publish_policy(
    policy_id: uuid.UUID,
    request: Request,
    body: WorkforcePolicyPublishIn = Body(...),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).publish_policy(org_id=resolved_org_id, policy_id=policy_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, resolved_org_id, "workforce.policy.publish", "workforce_policy", str(row.id), {})
    await _notify_workforce_event(
        db,
        org_id=resolved_org_id,
        title="Policy published",
        message=f"Policy {row.code} was published.",
        link="/app/workforce/hr",
        metadata_json={"policy_id": str(row.id), "policy_code": row.code},
    )
    await db.commit()
    return WorkforcePolicyOut.model_validate(row, from_attributes=True)


@router.get("/policies/{policy_id}/acks", response_model=list[WorkforcePolicyAckOut])
async def list_policy_acks(
    policy_id: uuid.UUID,
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    try:
        rows = await _svc(db).list_policy_acks(org_id=resolved_org_id, policy_id=policy_id, limit=limit)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [WorkforcePolicyAckOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/policies/{policy_id}/ack", response_model=WorkforcePolicyAckOut)
async def acknowledge_policy(
    policy_id: uuid.UUID,
    request: Request,
    body: WorkforcePolicyAckCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).acknowledge_policy_for_employee(
            org_id=resolved_org_id,
            policy_id=policy_id,
            employee_id=body.employee_id,
            actor_user_id=user.id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.policy.ack",
        "workforce_policy_ack",
        str(row.id),
        {"policy_id": str(policy_id), "employee_id": str(body.employee_id)},
    )
    await db.commit()
    return WorkforcePolicyAckOut.model_validate(row, from_attributes=True)


# Documents
@router.post("/documents/upload", response_model=WorkforceDocumentOut)
async def upload_document(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    policy_id: uuid.UUID | None = Query(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    body = await file.read()
    if len(body) > _DOC_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=422, detail="File too large (max 15 MB)")
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    if ct == "image/jpg":
        ct = "image/jpeg"
    if ct not in _DOC_UPLOAD_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported content type; allowed: PDF, PNG, JPEG, plain text")
    safe = _safe_upload_filename(file.filename)
    key = f"workforce/hr/documents/{resolved_org_id}/{uuid.uuid4()}_{safe}"
    s3 = s3_client()
    settings = get_settings()
    ensure_bucket(s3)
    s3.put_object(Bucket=settings.minio_bucket, Key=key, Body=body, ContentType=ct)
    url = _presigned_url(object_key=key)
    try:
        row = await _svc(db).create_document(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            employee_id=employee_id,
            policy_id=policy_id,
            name=safe,
            content_type=ct,
            size_bytes=len(body),
            object_key=key,
            url=url,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.document.upload",
        "workforce_document",
        str(row.id),
        {"employee_id": str(employee_id) if employee_id else None, "policy_id": str(policy_id) if policy_id else None},
    )
    await db.commit()
    return WorkforceDocumentOut.model_validate(row, from_attributes=True)


@router.get("/documents", response_model=list[WorkforceDocumentOut])
async def list_documents(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    policy_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    limit: int = Query(default=500, ge=1, le=2000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    try:
        rows = await _svc(db).list_documents(
            org_id=resolved_org_id,
            employee_id=employee_id,
            policy_id=policy_id,
            include_inactive=include_inactive,
            limit=limit,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [WorkforceDocumentOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/documents/{document_id}/deactivate", response_model=dict)
async def deactivate_document(
    document_id: uuid.UUID,
    request: Request,
    body: WorkforceDocumentDeactivateIn = Body(...),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).deactivate_document(org_id=resolved_org_id, document_id=document_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, resolved_org_id, "workforce.document.deactivate", "workforce_document", str(row.id), {})
    await db.commit()
    return {"ok": True}


# Checklists
@router.get("/checklist", response_model=list[WorkforceChecklistItemOut])
async def list_checklist(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    kind: str | None = Query(default=None),
    include_done: bool = Query(default=True),
    limit: int = Query(default=5000, ge=1, le=10000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    try:
        rows = await _svc(db).list_checklist(
            org_id=resolved_org_id,
            employee_id=employee_id,
            kind=kind,
            include_done=include_done,
            limit=limit,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [WorkforceChecklistItemOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/checklist", response_model=WorkforceChecklistItemOut)
async def create_checklist_item(
    request: Request,
    body: WorkforceChecklistItemCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).create_checklist_item(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            employee_id=body.employee_id,
            kind=body.kind,
            title=body.title,
            details=body.details,
            due_date=body.due_date,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, resolved_org_id, "workforce.checklist.create", "workforce_checklist_item", str(row.id), {"kind": row.kind})
    await db.commit()
    return WorkforceChecklistItemOut.model_validate(row, from_attributes=True)


@router.post("/checklist/{item_id}/done", response_model=WorkforceChecklistItemOut)
async def set_checklist_done(
    item_id: uuid.UUID,
    request: Request,
    body: WorkforceChecklistDoneIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await _svc(db).set_checklist_done(org_id=resolved_org_id, item_id=item_id, done=body.is_done, actor_user_id=user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(user.id, resolved_org_id, "workforce.checklist.done", "workforce_checklist_item", str(row.id), {"is_done": row.is_done})
    if row.is_done:
        await _notify_workforce_event(
            db,
            org_id=resolved_org_id,
            title="Checklist item completed",
            message=f"{row.kind.title()} checklist item completed for employee {row.employee_id}.",
            link="/app/workforce/hr",
            metadata_json={"checklist_item_id": str(row.id), "employee_id": str(row.employee_id), "kind": row.kind},
        )
    await db.commit()
    return WorkforceChecklistItemOut.model_validate(row, from_attributes=True)

