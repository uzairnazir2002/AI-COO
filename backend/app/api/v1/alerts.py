import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.location_repo import LocationRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.alerts import (
    AlertAcknowledgeIn,
    AlertAssignIn,
    AlertHistoryItem,
    AlertHistoryOut,
    AlertOut,
    AlertsOut,
)
from app.domain.services.alerts_service import AlertsService
from app.domain.services.errors import NotFoundError
from app.domain.services.location_service import LocationService
from app.domain.services.read_cache_service import (
    alerts_cache_key,
    alerts_cache_prefix,
    analytics_summary_cache_prefix,
    cache_delete_prefix,
    cache_get_json,
    cache_set_json,
)

router = APIRouter()


@router.get("", response_model=AlertsOut)
async def list_alerts(
    org_id: uuid.UUID = Query(...),
    status: str | None = Query(default=None),
    assignee_user_id: uuid.UUID | None = Query(default=None),
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
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    normalized_status = status.upper() if status else None

    cache_key = alerts_cache_key(org_id, normalized_status, assignee_user_id, location_id)
    cached = await cache_get_json(cache_key)
    if isinstance(cached, dict):
        return AlertsOut.model_validate(cached)

    rows = await AlertsService(db, AlertRepo(db)).list_alerts(
        org_id,
        normalized_status,
        assigned_to_user_id=assignee_user_id,
        location_id=location_id,
    )
    result = AlertsOut(items=[AlertOut.model_validate(row) for row in rows])
    await cache_set_json(cache_key, result.model_dump(mode="json"), get_settings().alerts_cache_ttl_seconds)
    return result


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    repo = AlertRepo(db)
    alert = await repo.get(alert_id, org_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await AlertsService(db, repo).dismiss(alert)
    await AuditRepo(db).log(
        actor_user_id=user.id,
        org_id=org_id,
        action="alert.dismiss",
        entity_type="alert",
        entity_id=str(alert.id),
        metadata_json={"status": "DISMISSED"},
    )
    await db.commit()
    await cache_delete_prefix(alerts_cache_prefix(org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(org_id))
    return {"ok": True}


@router.post("/{alert_id}/assign", response_model=dict)
async def assign_alert(
    alert_id: uuid.UUID,
    body: AlertAssignIn = Body(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    repo = AlertRepo(db)
    alert = await repo.get(alert_id, body.org_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if body.assignee_user_id is not None:
        assignee_membership = await OrgRepo(db).membership(body.assignee_user_id, body.org_id)
        if not assignee_membership:
            raise HTTPException(status_code=404, detail="Assignee is not a member of organization")

    await AlertsService(db, repo).assign(
        alert=alert,
        assignee_user_id=body.assignee_user_id,
        actor_user_id=user.id,
    )
    await AuditRepo(db).log(
        actor_user_id=user.id,
        org_id=body.org_id,
        action="alert.assign",
        entity_type="alert",
        entity_id=str(alert.id),
        metadata_json={"assigned_to_user_id": str(body.assignee_user_id) if body.assignee_user_id else None},
    )
    await db.commit()
    await cache_delete_prefix(alerts_cache_prefix(body.org_id))
    await cache_delete_prefix(analytics_summary_cache_prefix(body.org_id))
    return {"ok": True, "alert": AlertOut.model_validate(alert)}


@router.post("/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    body: AlertAcknowledgeIn = Body(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=body.org_id, user=user, db=db)
    repo = AlertRepo(db)
    alert = await repo.get(alert_id, body.org_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await AlertsService(db, repo).acknowledge(alert=alert)
    await AuditRepo(db).log(
        actor_user_id=user.id,
        org_id=body.org_id,
        action="alert.acknowledge",
        entity_type="alert",
        entity_id=str(alert.id),
        metadata_json={"acknowledged": True},
    )
    await db.commit()
    await cache_delete_prefix(alerts_cache_prefix(body.org_id))
    return {"ok": True, "alert": AlertOut.model_validate(alert)}


@router.get("/{alert_id}/history", response_model=AlertHistoryOut)
async def alert_history(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    repo = AlertRepo(db)
    alert = await repo.get(alert_id, org_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    logs = await AuditRepo(db).list_entity_events(
        org_id=org_id,
        entity_type="alert",
        entity_id=str(alert_id),
        actions=["alert.detect.budget_threshold", "alert.assign", "alert.acknowledge", "alert.dismiss"],
        limit=100,
    )
    return AlertHistoryOut(
        items=[
            AlertHistoryItem(
                id=row.id,
                action=row.action,
                actor_user_id=row.actor_user_id,
                metadata_json=row.metadata_json,
                created_at=row.created_at,
            )
            for row in logs
        ]
    )
