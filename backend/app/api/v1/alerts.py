import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.schemas.alerts import AlertOut, AlertsOut
from app.domain.services.alerts_service import AlertsService
from app.domain.services.read_cache_service import (
    alerts_cache_key,
    alerts_cache_prefix,
    analytics_summary_cache_prefix,
    cache_delete_prefix,
    cache_get_json,
    cache_set_json,
)
from app.core.config import get_settings

router = APIRouter()


@router.get("", response_model=AlertsOut)
async def list_alerts(
    org_id: uuid.UUID = Query(...),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    settings = get_settings()
    cache_key = alerts_cache_key(org_id, status)
    cached = await cache_get_json(cache_key)
    if isinstance(cached, dict):
        return AlertsOut.model_validate(cached)
    svc = AlertsService(db, AlertRepo(db))
    rows = await svc.list_alerts(org_id, status)
    result = AlertsOut(items=[AlertOut.model_validate(r, from_attributes=True) for r in rows])
    await cache_set_json(cache_key, result.model_dump(mode="json"), settings.alerts_cache_ttl_seconds)
    return result


@router.post("/{alert_id}/dismiss")
async def dismiss(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = AlertsService(db, AlertRepo(db))
    alert = await AlertRepo(db).get(alert_id, org_id)
    if alert:
        await svc.dismiss(alert)
        await db.commit()
        await cache_delete_prefix(alerts_cache_prefix(org_id))
        await cache_delete_prefix(analytics_summary_cache_prefix(org_id))
    return {"ok": True}
