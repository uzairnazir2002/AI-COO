import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.core.config import get_settings as get_app_settings
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.organization import (
    InviteIn,
    MemberOut,
    OrganizationCreateIn,
    OrganizationOut,
    OrgSettingsOut,
    OrgSettingsUpdateIn,
)
from app.domain.services.org_service import OrgService

router = APIRouter()


@router.post("", response_model=OrganizationOut)
async def create_org(body: OrganizationCreateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db))
    org = await svc.create_org(user.id, body.name)
    await db.commit()
    return OrganizationOut(org_id=org.id, name=org.name)


@router.get("", response_model=list[OrganizationOut])
async def list_orgs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await OrgRepo(db).list_orgs_for_user(user.id)
    return [OrganizationOut(org_id=o.id, name=o.name, role=str(m.role)) for o, m in rows]


@router.post("/{org_id}/invite")
async def invite(
    org_id: uuid.UUID,
    body: InviteIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    svc = OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db))
    invite_token = await svc.invite(user.id, org_id, body.email, body.role)
    await db.commit()
    if get_app_settings().expose_invite_token_in_response:
        return {"ok": True, "invite_token": invite_token}
    return {"ok": True}


@router.get("/{org_id}/members", response_model=list[MemberOut])
async def members(
    org_id: uuid.UUID,
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    rows = await OrgRepo(db).members(org_id)
    return [MemberOut(user_id=u.id, email=u.email, role=str(m.role)) for m, u in rows]


@router.get("/{org_id}/settings", response_model=OrgSettingsOut)
async def get_settings(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    settings = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db)).get_settings(org_id)
    return OrgSettingsOut(
        org_id=org_id,
        starting_cash=settings.starting_cash,
        runway_alert_threshold_days=settings.runway_alert_threshold_days,
        vendor_concentration_threshold_pct=settings.vendor_concentration_threshold_pct,
        misc_growth_multiplier=settings.misc_growth_multiplier,
        anomaly_spike_multiplier=settings.anomaly_spike_multiplier,
    )


@router.put("/{org_id}/settings", response_model=OrgSettingsOut)
async def update_settings(
    org_id: uuid.UUID,
    body: OrgSettingsUpdateIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER", "EDITOR")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    settings = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db)).update_settings(user.id, org_id, body)
    await db.commit()
    return OrgSettingsOut(
        org_id=org_id,
        starting_cash=settings.starting_cash,
        runway_alert_threshold_days=settings.runway_alert_threshold_days,
        vendor_concentration_threshold_pct=settings.vendor_concentration_threshold_pct,
        misc_growth_multiplier=settings.misc_growth_multiplier,
        anomaly_spike_multiplier=settings.anomaly_spike_multiplier,
    )
