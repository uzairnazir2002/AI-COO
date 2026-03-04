import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.alerts_repo import AlertRepo
from app.domain.schemas.alerts import AlertOut, AlertsOut
from app.domain.services.alerts_service import AlertsService

router = APIRouter()


@router.get("", response_model=AlertsOut)
async def list_alerts(
    org_id: uuid.UUID = Query(...),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    svc = AlertsService(db, AlertRepo(db))
    rows = await svc.list_alerts(org_id, status)
    return AlertsOut(items=[AlertOut.model_validate(r, from_attributes=True) for r in rows])


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
    return {"ok": True}
