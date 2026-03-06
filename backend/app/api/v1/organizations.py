import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_org_context, require_roles
from app.core.config import get_settings as get_app_settings
from app.db.session import get_db
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.plan_repo import PlanRepo
from app.domain.schemas.billing import BillingCheckoutIn, BillingCheckoutOut, BillingPortalIn, BillingPortalOut
from app.domain.schemas.organization import InviteIn, MemberOut, OrgBillingOut, OrgBillingUpdateIn, OrganizationCreateIn, OrganizationOut, OrgSettingsOut, OrgSettingsUpdateIn, PlanUsageOut
from app.domain.services.billing_service import BillingService
from app.domain.services.org_service import OrgService
from app.domain.services.usage_service import UsageService

router = APIRouter()


def _billing_out(billing) -> OrgBillingOut:
    return OrgBillingOut(
        org_id=billing.org_id,
        billing_email=billing.billing_email,
        invoice_enabled=billing.invoice_enabled,
        plan_label=billing.plan_label,
        billing_notes=billing.billing_notes,
        provider=getattr(billing, "provider", "MANUAL"),
        customer_id=getattr(billing, "customer_id", None),
        subscription_id=getattr(billing, "subscription_id", None),
        subscription_status=getattr(billing, "subscription_status", None),
        current_period_end=billing.current_period_end.isoformat() if getattr(billing, "current_period_end", None) else None,
        active_price_id=getattr(billing, "active_price_id", None),
        publishable_key=get_app_settings().stripe_publishable_key or None,
    )


@router.post("", response_model=OrganizationOut)
async def create_org(body: OrganizationCreateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db))
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
    svc = OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db))
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
    settings = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db)).get_settings(org_id)
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
    settings = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db)).update_settings(user.id, org_id, body)
    await db.commit()
    return OrgSettingsOut(
        org_id=org_id,
        starting_cash=settings.starting_cash,
        runway_alert_threshold_days=settings.runway_alert_threshold_days,
        vendor_concentration_threshold_pct=settings.vendor_concentration_threshold_pct,
        misc_growth_multiplier=settings.misc_growth_multiplier,
        anomaly_spike_multiplier=settings.anomaly_spike_multiplier,
    )


@router.get("/{org_id}/plan-usage", response_model=PlanUsageOut)
async def get_plan_usage(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    overview = await UsageService(PlanRepo(db)).get_usage_overview(org_id)
    return PlanUsageOut(
        plan_code=overview["plan_code"],
        period_start=overview["period_start"].isoformat(),
        metrics=overview["metrics"],
    )


@router.get("/{org_id}/billing", response_model=OrgBillingOut)
async def get_billing(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    billing = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db)).get_billing(org_id)
    await db.commit()
    return _billing_out(billing)


@router.put("/{org_id}/billing", response_model=OrgBillingOut)
async def update_billing(
    org_id: uuid.UUID,
    body: OrgBillingUpdateIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    billing = await OrgService(OrgRepo(db), AuthRepo(db), AuditRepo(db), OutboxRepo(db)).update_billing(
        actor_user_id=user.id,
        org_id=org_id,
        billing_email=body.billing_email,
        invoice_enabled=body.invoice_enabled,
        plan_label=body.plan_label,
        billing_notes=body.billing_notes,
    )
    await db.commit()
    return _billing_out(billing)


@router.post("/{org_id}/billing/checkout", response_model=BillingCheckoutOut)
async def create_billing_checkout(
    org_id: uuid.UUID,
    body: BillingCheckoutIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    org_repo = OrgRepo(db)
    org = await org_repo.get_org(org_id)
    billing = await OrgService(org_repo, AuthRepo(db), AuditRepo(db), OutboxRepo(db)).get_billing(org_id)
    service = BillingService(
        settings=get_app_settings(),
        org_repo=org_repo,
        audit_repo=AuditRepo(db),
        notification_repo=NotificationRepo(db),
    )
    url = await service.create_checkout_session(
        actor_user_id=user.id,
        org_name=org.name if org else "AI COO Organization",
        billing=billing,
        price_id=body.price_id,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )
    await db.commit()
    return BillingCheckoutOut(url=url)


@router.post("/{org_id}/billing/portal", response_model=BillingPortalOut)
async def create_billing_portal(
    org_id: uuid.UUID,
    body: BillingPortalIn,
    user: User = Depends(get_current_user),
    _: object = Depends(require_roles("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    await get_org_context(org_id=org_id, user=user, db=db)
    org_repo = OrgRepo(db)
    org = await org_repo.get_org(org_id)
    billing = await OrgService(org_repo, AuthRepo(db), AuditRepo(db), OutboxRepo(db)).get_billing(org_id)
    service = BillingService(
        settings=get_app_settings(),
        org_repo=org_repo,
        audit_repo=AuditRepo(db),
        notification_repo=NotificationRepo(db),
    )
    url = await service.create_portal_session(
        actor_user_id=user.id,
        org_name=org.name if org else "AI COO Organization",
        billing=billing,
        return_url=body.return_url,
    )
    await db.commit()
    return BillingPortalOut(url=url)


@router.post("/billing/webhook")
async def billing_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_app_settings()
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        if settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.stripe_webhook_secret)
        else:
            event = stripe.Event.construct_from(await request.json(), settings.stripe_secret_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc

    if event["type"] not in {"customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted", "checkout.session.completed"}:
        return {"ok": True}

    data = event["data"]["object"]
    metadata = data.get("metadata") or {}
    org_repo = OrgRepo(db)
    org_id = metadata.get("org_id")
    if not org_id and data.get("customer"):
        billing = await org_repo.get_billing_by_customer_id(data["customer"])
        org_id = str(billing.org_id) if billing else None
    if not org_id:
        return {"ok": True}

    item = None
    if data.get("items", {}).get("data"):
        item = data["items"]["data"][0]

    current_period_end = None
    if data.get("current_period_end"):
        current_period_end = datetime.fromtimestamp(data["current_period_end"], tz=timezone.utc)

    await BillingService(
        settings=settings,
        org_repo=org_repo,
        audit_repo=AuditRepo(db),
        notification_repo=NotificationRepo(db),
    ).sync_from_subscription(
        org_id=uuid.UUID(org_id),
        subscription_id=data.get("id") if "subscription" in event["type"] else data.get("subscription"),
        customer_id=data.get("customer"),
        status=data.get("status"),
        price_id=(item.get("price", {}) or {}).get("id") if item else None,
        current_period_end=current_period_end,
    )
    await db.commit()
    return {"ok": True}
