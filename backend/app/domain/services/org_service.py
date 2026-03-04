import hashlib
import secrets
import uuid
from datetime import timedelta

from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.auth_repo import AuthRepo
from app.domain.repos.org_repo import OrgRepo
from app.domain.schemas.organization import OrgSettingsUpdateIn
from app.domain.services.errors import ConflictError, ForbiddenError, NotFoundError
from app.utils.time import utc_now


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class OrgService:
    def __init__(self, org_repo: OrgRepo, auth_repo: AuthRepo, audit_repo: AuditRepo):
        self.org_repo = org_repo
        self.auth_repo = auth_repo
        self.audit_repo = audit_repo

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
            "misc_growth_multiplier",
            "anomaly_spike_multiplier",
        ):
            value = getattr(body, field)
            if value is not None:
                setattr(settings, field, value)
                changed[field] = str(value)
        await self.org_repo.save_settings(settings)
        await self.audit_repo.log(actor_user_id, org_id, "org.settings.update", "organization_settings", str(settings.id), changed)
        return settings


ROLE_WEIGHT = {"VIEWER": 1, "EDITOR": 2, "OWNER": 3}


def require_role(actual: str, allowed: list[str]):
    if actual not in allowed:
        raise ForbiddenError("Forbidden")
