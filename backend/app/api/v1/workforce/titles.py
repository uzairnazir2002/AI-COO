import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.workforce_title_repo import WorkforceTitleRepo
from app.domain.schemas.workforce import WorkforceTitleCreateIn, WorkforceTitleOut, WorkforceTitleUpdateIn
from app.domain.services.errors import NotFoundError
from app.domain.services.workforce_title_service import WorkforceTitleService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[WorkforceTitleOut])
async def list_titles(
    org_id: uuid.UUID = Query(...),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await WorkforceTitleService(WorkforceTitleRepo(db)).list_titles(
        org_id=org_id, include_inactive=include_inactive
    )
    return [WorkforceTitleOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=WorkforceTitleOut)
async def create_title(
    body: WorkforceTitleCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceTitleService(WorkforceTitleRepo(db))
    try:
        row = await svc.create_title(
            org_id=body.org_id,
            actor_user_id=user.id,
            name=body.name,
            level=body.level,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.title.create",
        "workforce_title",
        str(row.id),
        {"name": row.name, "level": row.level, "is_active": row.is_active},
    )
    await db.commit()
    return WorkforceTitleOut.model_validate(row, from_attributes=True)


@router.put("/{title_id}", response_model=WorkforceTitleOut)
async def update_title(
    title_id: uuid.UUID,
    body: WorkforceTitleUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceTitleService(WorkforceTitleRepo(db))
    try:
        row = await svc.update_title(
            org_id=body.org_id,
            title_id=title_id,
            name=body.name,
            level=body.level,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "workforce.title.update",
        "workforce_title",
        str(row.id),
        {"name": row.name, "level": row.level, "is_active": row.is_active},
    )
    await db.commit()
    return WorkforceTitleOut.model_validate(row, from_attributes=True)


@router.delete("/{title_id}")
async def delete_title(
    title_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = WorkforceTitleService(WorkforceTitleRepo(db))
    try:
        row = await svc.deactivate_title(org_id=org_id, title_id=title_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        org_id,
        "workforce.title.deactivate",
        "workforce_title",
        str(row.id),
        {"name": row.name},
    )
    await db.commit()
    return {"ok": True}

