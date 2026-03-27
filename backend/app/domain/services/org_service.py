import hashlib
import secrets
import uuid
from datetime import timedelta

from app.core.pii_crypto import pii_decrypt, pii_encrypt
from app.domain.models.organization_billing import OrganizationBilling
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.notification_repo import NotificationRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.organization import OrgSettingsUpdateIn
from app.domain.services.errors import ConflictError, ForbiddenError, NotFoundError
from app.domain.services.notification_service import NotificationService
from app.utils.time import utc_now


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class OrgService:
    def __init__(self, org_repo: OrgRepo, auth_repo: AuthRepo, audit_repo: AuditRepo, outbox_repo: OutboxRepo | None = None):
        self.org_repo = org_repo
        self.auth_repo = auth_repo
        self.audit_repo = audit_repo
        self.outbox_repo = outbox_repo

    async def _notify(
        self,
        *,
        org_id: uuid.UUID,
        category: str,
        title: str,
        message: str | None = None,
        link: str | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        await NotificationService(NotificationRepo(self.org_repo.db)).create_org_notification(
            org_id=org_id,
            category=category,
            title=title,
            message=message,
            link=link,
            metadata_json=metadata_json or {},
        )

    async def create_org(self, user_id: uuid.UUID, name: str):
        org = await self.org_repo.create_org(name)
        await self.org_repo.add_membership(user_id, org.id, "OWNER")
        await self.audit_repo.log(user_id, org.id, "org.create", "organization", str(org.id), {"name": name})
        return org

    async def list_orgs(self, user_id: uuid.UUID):
        return await self.org_repo.list_orgs_for_user(user_id)

    async def invite(self, actor_user_id: uuid.UUID, org_id: uuid.UUID, email: str, role: str) -> str:
        existing = await self.auth_repo.get_user_by_email(email.lower())
        if existing:
            membership = await self.org_repo.membership(existing.id, org_id)
            if membership:
                raise ConflictError("Already member")
        raw_token = secrets.token_urlsafe(32)
        invite = await self.org_repo.create_invite(
            org_id=org_id,
            email=email.lower(),
            role=role,
            invited_by=actor_user_id,
            token_hash=_token_hash(raw_token),
            expires_at=utc_now() + timedelta(days=7),
        )
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "org.invite",
            "organization_invite",
            str(invite.id),
            {"role": role, "email": email},
        )
        await self._notify(
            org_id=org_id,
            category="ORG",
            title="Member invited",
            message=f"{email.lower()} was invited as {role}.",
            link="/app/settings",
            metadata_json={"email": email.lower(), "role": role},
        )
        if self.outbox_repo is not None:
            await self.outbox_repo.create_event(
                org_id=org_id,
                event_type="email.send",
                payload={
                    "to": email.lower(),
                    "subject": "You are invited to AI COO",
                    "body": (
                        "You were invited to join your organization in AI COO.\n\n"
                        f"Invite token: {raw_token}\n"
                        "Use this token in the invite acceptance flow."
                    ),
                },
                dedupe_key=f"invite-email:{invite.id}",
                max_attempts=5,
            )
        return raw_token

    async def members(self, org_id: uuid.UUID):
        return await self.org_repo.members(org_id)

    async def get_settings(self, org_id: uuid.UUID):
        settings = await self.org_repo.get_settings(org_id)
        if not settings:
            raise NotFoundError("Organization settings not found")
        return settings

    async def update_settings(self, actor_user_id: uuid.UUID, org_id: uuid.UUID, body: OrgSettingsUpdateIn):
        settings = await self.get_settings(org_id)
        changed = {}
        for field in (
            "starting_cash",
            "runway_alert_threshold_days",
            "vendor_concentration_threshold_pct",
            "budget_variance_alert_threshold_pct",
            "misc_growth_multiplier",
            "anomaly_spike_multiplier",
            "owner_mfa_required",
            "owner_session_max_minutes",
            "sensitive_action_reauth_minutes",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(settings, field, value)
                changed[field] = str(value)
        await self.org_repo.save_settings(settings)
        await self.audit_repo.log(actor_user_id, org_id, "org.settings.update", "organization_settings", str(settings.id), changed)
        if changed:
            await self._notify(
                org_id=org_id,
                category="SETTINGS",
                title="Financial settings updated",
                message="Organization financial thresholds were updated.",
                link="/app/settings",
                metadata_json=changed,
            )
        return settings

    async def get_billing(self, org_id: uuid.UUID) -> OrganizationBilling:
        billing = await self.org_repo.get_billing(org_id)
        if not billing:
            billing = OrganizationBilling(
                org_id=org_id,
                billing_email=None,
                invoice_enabled=False,
                plan_label="FREE",
                billing_notes=None,
            )
            await self.org_repo.save_billing(billing)
        billing.billing_email = pii_decrypt(billing.billing_email)
        return billing

    async def update_billing(
        self,
        actor_user_id: uuid.UUID,
        org_id: uuid.UUID,
        billing_email: str | None,
        invoice_enabled: bool | None,
        plan_label: str | None,
        billing_notes: str | None,
    ) -> OrganizationBilling:
        billing = await self.get_billing(org_id)
        changed = {}
        if billing_email is not None:
            billing.billing_email = pii_encrypt(str(billing_email))
            changed["billing_email"] = billing_email
        if invoice_enabled is not None:
            billing.invoice_enabled = invoice_enabled
            changed["invoice_enabled"] = invoice_enabled
        if plan_label is not None:
            billing.plan_label = plan_label
            changed["plan_label"] = plan_label
        if billing_notes is not None:
            billing.billing_notes = billing_notes
            changed["billing_notes"] = billing_notes
        await self.org_repo.save_billing(billing)
        await self.audit_repo.log(actor_user_id, org_id, "org.billing.update", "organization_billing", str(billing.id), changed)
        if changed:
            await self._notify(
                org_id=org_id,
                category="BILLING",
                title="Billing settings updated",
                message="Owner billing settings changed.",
                link="/app/settings",
                metadata_json=changed,
            )
        billing.billing_email = pii_decrypt(billing.billing_email)
        return billing


ROLE_WEIGHT = {"VIEWER": 1, "EDITOR": 2, "OWNER": 3}


def require_role(actual: str, allowed: list[str]):
    if actual not in allowed:
        raise ForbiddenError("Forbidden")
