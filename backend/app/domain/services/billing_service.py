import stripe

from app.core.config import Settings
from app.domain.models.organization_billing import OrganizationBilling
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.services.errors import ConflictError
from app.domain.services.notification_service import NotificationService


class BillingService:
    def __init__(self, *, settings: Settings, org_repo: OrgRepo, audit_repo: AuditRepo, notification_repo: NotificationRepo):
        self.settings = settings
        self.org_repo = org_repo
        self.audit_repo = audit_repo
        self.notifications = NotificationService(notification_repo)
        stripe.api_key = settings.stripe_secret_key

    def _ensure_configured(self) -> None:
        if not self.settings.stripe_secret_key:
            raise ConflictError("Stripe billing is not configured")

    async def _ensure_customer(self, billing: OrganizationBilling, *, org_name: str) -> OrganizationBilling:
        if billing.customer_id:
            return billing
        self._ensure_configured()
        customer = stripe.Customer.create(
            email=billing.billing_email or None,
            name=org_name,
            metadata={"org_id": str(billing.org_id)},
        )
        billing.customer_id = customer["id"]
        billing.provider = "STRIPE"
        await self.org_repo.save_billing(billing)
        return billing

    async def create_checkout_session(
        self,
        *,
        actor_user_id,
        org_name: str,
        billing: OrganizationBilling,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        billing = await self._ensure_customer(billing, org_name=org_name)
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=billing.customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"org_id": str(billing.org_id), "actor_user_id": str(actor_user_id)},
        )
        await self.audit_repo.log(actor_user_id, billing.org_id, "billing.checkout.start", "organization_billing", str(billing.id), {"price_id": price_id})
        await self.notifications.create_org_notification(
            org_id=billing.org_id,
            category="BILLING",
            title="Billing checkout created",
            message="A Stripe checkout session is ready for the selected subscription plan.",
            link="/app/settings",
            metadata_json={"price_id": price_id},
        )
        return session["url"]

    async def create_portal_session(self, *, actor_user_id, org_name: str, billing: OrganizationBilling, return_url: str) -> str:
        billing = await self._ensure_customer(billing, org_name=org_name)
        session = stripe.billing_portal.Session.create(customer=billing.customer_id, return_url=return_url)
        await self.audit_repo.log(actor_user_id, billing.org_id, "billing.portal.open", "organization_billing", str(billing.id), {})
        return session["url"]

    async def sync_from_subscription(
        self,
        *,
        org_id,
        subscription_id: str | None,
        customer_id: str | None,
        status: str | None,
        price_id: str | None,
        current_period_end,
    ) -> OrganizationBilling:
        billing = await self.org_repo.get_billing(org_id)
        if not billing:
            billing = OrganizationBilling(org_id=org_id, plan_label="FREE", provider="STRIPE")
        billing.provider = "STRIPE"
        billing.customer_id = customer_id
        billing.subscription_id = subscription_id
        billing.subscription_status = status
        billing.active_price_id = price_id
        billing.current_period_end = current_period_end
        if status:
            billing.plan_label = status.upper()
        await self.org_repo.save_billing(billing)
        await self.notifications.create_org_notification(
            org_id=org_id,
            category="BILLING",
            title="Subscription updated",
            message=f"Subscription status is now {status or 'unknown'}.",
            link="/app/settings",
            metadata_json={"subscription_id": subscription_id, "price_id": price_id},
        )
        return billing
