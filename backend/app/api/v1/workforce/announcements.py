import re
import uuid
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_sensitive_reauth, resolve_workforce_org_id_from_request
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.models.outbox_event import OutboxEvent
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_announcement_repo import WorkforceAnnouncementRepo
from app.domain.schemas.workforce_announcement import (
    WorkforceAnnouncementAcknowledgeIn,
    WorkforceAnnouncementArchiveIn,
    WorkforceAnnouncementAttachmentUploadOut,
    WorkforceAnnouncementCreateIn,
    WorkforceAnnouncementDeliveryListOut,
    WorkforceAnnouncementDeliveryOut,
    WorkforceAnnouncementDetailOut,
    WorkforceAnnouncementOut,
    WorkforceAnnouncementPublishIn,
    WorkforceAnnouncementReceiptOut,
    WorkforceAnnouncementTemplateCreateIn,
    WorkforceAnnouncementTemplateOut,
    WorkforceAnnouncementTemplateUpdateIn,
    WorkforceAnnouncementUpdateIn,
    WorkforceAutomationKeysOut,
)
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_announcement_automation import AUTOMATION_KEYS_KNOWN
from app.domain.services.workforce_announcement_service import (
    build_workforce_announcement_service,
    build_workforce_announcement_template_service,
)
from app.infra.s3 import ensure_bucket, s3_client

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_out(row, receipt=None) -> WorkforceAnnouncementOut:
    rec = None
    if receipt is not None:
        rec = WorkforceAnnouncementReceiptOut.model_validate(receipt, from_attributes=True)
    base = WorkforceAnnouncementOut.model_validate(row, from_attributes=True)
    return base.model_copy(update={"my_receipt": rec})


_ANNOUNCEMENT_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
_ANNOUNCEMENT_UPLOAD_TYPES = frozenset(
    {"application/pdf", "image/png", "image/jpeg", "image/jpg", "text/plain"}
)
_SAFE_FILENAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_upload_filename(name: str | None) -> str:
    base = (name or "attachment").split("/")[-1].split("\\")[-1]
    cleaned = _SAFE_FILENAME.sub("_", base).strip("._") or "attachment"
    return cleaned[:180]


def _presigned_attachment_url(*, object_key: str, filename: str) -> str:
    s3 = s3_client()
    settings = get_settings()
    ensure_bucket(s3)
    bucket = settings.minio_bucket
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=7 * 24 * 3600,
    )
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


async def _enrich_deliveries(db: AsyncSession, rows: list) -> list[WorkforceAnnouncementDeliveryOut]:
    ids = [r.outbox_event_id for r in rows if r.outbox_event_id]
    ob_map: dict[uuid.UUID, OutboxEvent] = {}
    if ids:
        q = await db.execute(select(OutboxEvent).where(OutboxEvent.id.in_(ids)))
        for ev in q.scalars().all():
            ob_map[ev.id] = ev
    out: list[WorkforceAnnouncementDeliveryOut] = []
    for r in rows:
        extra: dict = {}
        if r.outbox_event_id and r.outbox_event_id in ob_map:
            ev = ob_map[r.outbox_event_id]
            extra = {
                "outbox_status": ev.status,
                "outbox_attempts": ev.attempts,
                "outbox_last_error": ev.last_error,
            }
        base = WorkforceAnnouncementDeliveryOut.model_validate(r, from_attributes=True)
        out.append(base.model_copy(update=extra))
    return out


@router.get("/automation-keys", response_model=WorkforceAutomationKeysOut)
async def list_automation_keys(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    return WorkforceAutomationKeysOut(keys=sorted(AUTOMATION_KEYS_KNOWN))


@router.post("/attachments/upload", response_model=WorkforceAnnouncementAttachmentUploadOut)
async def upload_announcement_attachment(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    body = await file.read()
    if len(body) > _ANNOUNCEMENT_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=422, detail="File too large (max 10 MB)")
    ct = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    if ct == "image/jpg":
        ct = "image/jpeg"
    if ct not in _ANNOUNCEMENT_UPLOAD_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Unsupported content type; allowed: PDF, PNG, JPEG, plain text",
        )
    safe = _safe_upload_filename(file.filename)
    key = f"workforce/announcements/{resolved_org_id}/{uuid.uuid4()}_{safe}"
    s3 = s3_client()
    settings = get_settings()
    ensure_bucket(s3)
    bucket = settings.minio_bucket
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=ct)
    url = _presigned_attachment_url(object_key=key, filename=safe)
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.attachment.upload",
        "workforce_announcement_attachment",
        key,
        {"size": len(body), "content_type": ct},
    )
    await db.commit()
    return WorkforceAnnouncementAttachmentUploadOut(
        name=safe,
        url=url,
        content_type=ct,
        size_bytes=len(body),
    )


@router.get("/templates", response_model=list[WorkforceAnnouncementTemplateOut])
async def list_announcement_templates(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    rows = await build_workforce_announcement_template_service(db).list_templates(
        org_id=resolved_org_id, include_inactive=include_inactive
    )
    return [WorkforceAnnouncementTemplateOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/templates", response_model=WorkforceAnnouncementTemplateOut)
async def create_announcement_template(
    request: Request,
    body: WorkforceAnnouncementTemplateCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await build_workforce_announcement_template_service(db).create(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            name=body.name,
            body_template=body.body_template,
            code=body.code,
            description=body.description,
            automation_key=body.automation_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement_template.create",
        "workforce_announcement_template",
        str(row.id),
        {"name": row.name},
    )
    await db.commit()
    return WorkforceAnnouncementTemplateOut.model_validate(row, from_attributes=True)


@router.put("/templates/{template_id}", response_model=WorkforceAnnouncementTemplateOut)
async def update_announcement_template(
    template_id: uuid.UUID,
    request: Request,
    body: WorkforceAnnouncementTemplateUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    fs = body.model_fields_set
    try:
        row = await build_workforce_announcement_template_service(db).update(
            org_id=resolved_org_id,
            template_id=template_id,
            name=body.name if "name" in fs else None,
            body_template=body.body_template if "body_template" in fs else None,
            code=body.code if "code" in fs else None,
            code_clear=body.code_clear,
            description=body.description if "description" in fs else None,
            description_clear=body.description_clear,
            automation_key=body.automation_key if "automation_key" in fs else None,
            automation_clear=body.automation_clear,
            is_active=body.is_active if "is_active" in fs else None,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement_template.update",
        "workforce_announcement_template",
        str(row.id),
        {},
    )
    await db.commit()
    return WorkforceAnnouncementTemplateOut.model_validate(row, from_attributes=True)


@router.get("", response_model=list[WorkforceAnnouncementOut])
async def list_announcements(
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    rows = await build_workforce_announcement_service(db).list_for_user(
        org_id=resolved_org_id,
        user_id=user.id,
        user_email=user.email,
        role=ctx.role,
        include_archived=include_archived,
        limit=200,
    )
    out: list[WorkforceAnnouncementOut] = []
    repo = WorkforceAnnouncementRepo(db)
    for row in rows:
        rec = await repo.get_receipt(announcement_id=row.id, user_id=user.id)
        out.append(_to_out(row, rec))
    return out


@router.post("", response_model=WorkforceAnnouncementOut)
async def create_announcement(
    request: Request,
    body: WorkforceAnnouncementCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    att = None
    if body.attachments is not None:
        att = [a.model_dump() for a in body.attachments]
    try:
        row = await build_workforce_announcement_service(db).create(
            org_id=resolved_org_id,
            actor_user_id=user.id,
            title=body.title,
            body=body.body,
            priority=body.priority,
            pinned=body.pinned,
            acknowledgement_required=body.acknowledgement_required,
            expires_at=body.expires_at,
            scheduled_publish_at=body.scheduled_publish_at,
            audience_kind=body.audience_kind,
            audience_ids=body.audience_ids,
            attachments_json=att,
            send_email_on_publish=body.send_email_on_publish,
            template_id=body.template_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.create",
        "workforce_announcement",
        str(row.id),
        {"title": row.title},
    )
    await db.commit()
    return _to_out(row, None)


@router.get("/{announcement_id}/deliveries", response_model=WorkforceAnnouncementDeliveryListOut)
async def list_announcement_deliveries(
    announcement_id: uuid.UUID,
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None, description="Filter: PENDING, RETRYING, SENT, FAILED, or ALL"),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        rows, total = await build_workforce_announcement_service(db).list_deliveries_page(
            org_id=resolved_org_id,
            announcement_id=announcement_id,
            status=status,
            page=page,
            page_size=page_size,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = await _enrich_deliveries(db, rows)
    return WorkforceAnnouncementDeliveryListOut(items=items, total=total, page=page, page_size=page_size)


@router.put("/{announcement_id}", response_model=WorkforceAnnouncementOut)
async def update_announcement(
    request: Request,
    announcement_id: uuid.UUID,
    body: WorkforceAnnouncementUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    fs = body.model_fields_set
    att: list[dict] | None = None
    attachments_clear_arg = body.attachments_clear
    if "attachments" in fs:
        if body.attachments is None:
            attachments_clear_arg = True
        else:
            att = [a.model_dump() for a in body.attachments]
    try:
        row = await build_workforce_announcement_service(db).update(
            org_id=resolved_org_id,
            announcement_id=announcement_id,
            title=body.title if "title" in fs else None,
            body=body.body if "body" in fs else None,
            priority=body.priority if "priority" in fs else None,
            pinned=body.pinned if "pinned" in fs else None,
            acknowledgement_required=body.acknowledgement_required if "acknowledgement_required" in fs else None,
            expires_at=body.expires_at if "expires_at" in fs and body.expires_at is not None else None,
            expires_at_clear="expires_at" in fs and body.expires_at is None,
            scheduled_publish_at=body.scheduled_publish_at
            if "scheduled_publish_at" in fs and body.scheduled_publish_at is not None
            else None,
            scheduled_publish_clear="scheduled_publish_at" in fs and body.scheduled_publish_at is None,
            audience_kind=body.audience_kind if "audience_kind" in fs else None,
            audience_ids=body.audience_ids if "audience_ids" in fs else None,
            audience_ids_clear=body.audience_ids_clear,
            attachments_json=att if "attachments" in fs and body.attachments is not None else None,
            attachments_clear=attachments_clear_arg,
            send_email_on_publish=body.send_email_on_publish if "send_email_on_publish" in fs else None,
            template_id=body.template_id if "template_id" in fs else None,
            template_clear=body.template_clear,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.update",
        "workforce_announcement",
        str(row.id),
        {},
    )
    await db.commit()
    rec = await WorkforceAnnouncementRepo(db).get_receipt(announcement_id=row.id, user_id=user.id)
    return _to_out(row, rec)


@router.post("/{announcement_id}/publish", response_model=WorkforceAnnouncementOut)
async def publish_announcement(
    request: Request,
    announcement_id: uuid.UUID,
    body: WorkforceAnnouncementPublishIn = Body(...),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await build_workforce_announcement_service(db).publish(org_id=resolved_org_id, announcement_id=announcement_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.publish",
        "workforce_announcement",
        str(row.id),
        {},
    )
    await db.commit()
    rec = await WorkforceAnnouncementRepo(db).get_receipt(announcement_id=row.id, user_id=user.id)
    return _to_out(row, rec)


@router.post("/{announcement_id}/archive", response_model=WorkforceAnnouncementOut)
async def archive_announcement(
    request: Request,
    announcement_id: uuid.UUID,
    body: WorkforceAnnouncementArchiveIn = Body(...),
    _reauth: None = Depends(require_sensitive_reauth()),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    try:
        row = await build_workforce_announcement_service(db).archive(org_id=resolved_org_id, announcement_id=announcement_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.archive",
        "workforce_announcement",
        str(row.id),
        {},
    )
    await db.commit()
    rec = await WorkforceAnnouncementRepo(db).get_receipt(announcement_id=row.id, user_id=user.id)
    return _to_out(row, rec)


@router.get("/{announcement_id}", response_model=WorkforceAnnouncementDetailOut)
async def get_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    org_id: uuid.UUID | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(org_id, request, db)
    ctx = await get_org_context(org_id=resolved_org_id, user=user, db=db)
    try:
        row, receipt = await build_workforce_announcement_service(db).get_and_mark_read(
            org_id=resolved_org_id,
            announcement_id=announcement_id,
            user_id=user.id,
            user_email=user.email,
            role=ctx.role,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    o = _to_out(row, receipt)
    return WorkforceAnnouncementDetailOut(**o.model_dump())


@router.post("/{announcement_id}/acknowledge", response_model=WorkforceAnnouncementReceiptOut)
async def acknowledge_announcement(
    request: Request,
    announcement_id: uuid.UUID,
    body: WorkforceAnnouncementAcknowledgeIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    resolved_org_id = await resolve_workforce_org_id_from_request(body.org_id, request, db)
    await get_org_context(org_id=resolved_org_id, user=user, db=db)
    try:
        rec = await build_workforce_announcement_service(db).acknowledge(
            org_id=resolved_org_id, announcement_id=announcement_id, user_id=user.id, user_email=user.email
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        resolved_org_id,
        "workforce.announcement.acknowledge",
        "workforce_announcement",
        str(announcement_id),
        {},
    )
    await db.commit()
    return WorkforceAnnouncementReceiptOut.model_validate(rec, from_attributes=True)
