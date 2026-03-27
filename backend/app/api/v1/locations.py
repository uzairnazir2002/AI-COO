import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.schemas.location import LocationCreateIn, LocationOut, LocationUpdateIn
from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService

router = APIRouter()


def _assert_mutation_role(role: str) -> None:
    if role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_model=list[LocationOut])
async def list_locations(
    org_id: uuid.UUID = Query(...),
    include_inactive: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    rows = await LocationService(LocationRepo(db)).list_locations(org_id=org_id, include_inactive=include_inactive)
    return [LocationOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=LocationOut)
async def create_location(
    body: LocationCreateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = LocationService(LocationRepo(db))
    try:
        location = await svc.create_location(
            org_id=body.org_id,
            actor_user_id=user.id,
            name=body.name,
            code=body.code,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "location.create",
        "location",
        str(location.id),
        {"name": location.name, "code": location.code, "is_active": location.is_active},
    )
    await db.commit()
    return LocationOut.model_validate(location, from_attributes=True)


@router.put("/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdateIn = Body(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=body.org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = LocationService(LocationRepo(db))
    try:
        location = await svc.update_location(
            org_id=body.org_id,
            location_id=location_id,
            name=body.name,
            code=body.code,
            is_active=body.is_active,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        body.org_id,
        "location.update",
        "location",
        str(location.id),
        {"name": location.name, "code": location.code, "is_active": location.is_active},
    )
    await db.commit()
    return LocationOut.model_validate(location, from_attributes=True)


@router.delete("/{location_id}")
async def delete_location(
    location_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ctx = await get_org_context(org_id=org_id, user=user, db=db)
    _assert_mutation_role(ctx.role)
    svc = LocationService(LocationRepo(db))
    try:
        location = await svc.deactivate_location(org_id=org_id, location_id=location_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await AuditRepo(db).log(
        user.id,
        org_id,
        "location.deactivate",
        "location",
        str(location.id),
        {"name": location.name},
    )
    await db.commit()
    return {"ok": True}
