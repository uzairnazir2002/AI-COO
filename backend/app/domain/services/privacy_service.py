import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.pii_crypto import (
    active_pii_key_id,
    pii_decrypt,
    pii_encrypt,
    pii_reencrypt,
)
from app.domain.models.membership import Membership
from app.domain.models.organization import Organization
from app.domain.models.organization_billing import OrganizationBilling
from app.domain.models.organization_invite import OrganizationInvite
from app.domain.models.token_session import TokenSession
from app.domain.models.user import User
from app.domain.repos.audit_repo import AuditRepo
from app.domain.repos.deletion_repo import DeletionRepo
from app.domain.services.errors import ConflictError, ForbiddenError
from app.utils.time import utc_now


class PrivacyService:
    def __init__(self, db: AsyncSession, audit_repo: AuditRepo, deletion_repo: DeletionRepo):
        self.db = db
        self.audit_repo = audit_repo
        self.deletion_repo = deletion_repo

    async def request_account_deletion(self, *, user_id: uuid.UUID, reason: str | None) -> dict:
        existing = await self.deletion_repo.latest_pending_for_user(user_id)
        if existing:
            raise ConflictError("Account deletion is already pending")
        now = utc_now()
        delete_after = now + timedelta(days=max(1, get_settings().deletion_grace_period_days))
        row = await self.deletion_repo.create_request(
            scope="USER",
            requested_by_user_id=user_id,
            target_user_id=user_id,
            target_org_id=None,
            reason=reason,
            delete_after=delete_after,
        )
        await self.audit_repo.log(
            user_id,
            None,
            "auth.delete.requested",
            "deletion_request",
            str(row.id),
            {"delete_after": delete_after.isoformat()},
        )
        return {"request_id": row.id, "delete_after": delete_after}

    async def list_account_deletion_requests(self, *, user_id: uuid.UUID, limit: int = 20) -> list:
        return await self.deletion_repo.list_for_user(user_id, limit=limit)

    async def request_org_deletion(
        self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID, reason: str | None
    ) -> dict:
        membership = await self.db.scalar(
            select(Membership).where(
                Membership.user_id == actor_user_id, Membership.org_id == org_id
            )
        )
        if not membership or str(membership.role) != "OWNER":
            raise ForbiddenError("Forbidden")
        existing = await self.deletion_repo.latest_pending_for_org(org_id)
        if existing:
            raise ConflictError("Organization deletion is already pending")
        now = utc_now()
        delete_after = now + timedelta(days=max(1, get_settings().deletion_grace_period_days))
        row = await self.deletion_repo.create_request(
            scope="ORG",
            requested_by_user_id=actor_user_id,
            target_user_id=None,
            target_org_id=org_id,
            reason=reason,
            delete_after=delete_after,
        )
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "org.delete.requested",
            "deletion_request",
            str(row.id),
            {"delete_after": delete_after.isoformat()},
        )
        return {"request_id": row.id, "delete_after": delete_after}

    async def list_org_deletion_requests(
        self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID, limit: int = 50
    ) -> list:
        membership = await self.db.scalar(
            select(Membership).where(
                Membership.user_id == actor_user_id, Membership.org_id == org_id
            )
        )
        if not membership or str(membership.role) != "OWNER":
            raise ForbiddenError("Forbidden")
        return await self.deletion_repo.list_for_org(org_id, limit=limit)

    async def rotate_org_pii(self, *, actor_user_id: uuid.UUID, org_id: uuid.UUID) -> dict:
        membership = await self.db.scalar(
            select(Membership).where(
                Membership.user_id == actor_user_id, Membership.org_id == org_id
            )
        )
        if not membership or str(membership.role) != "OWNER":
            raise ForbiddenError("Forbidden")
        rotated = 0
        billing = await self.db.scalar(
            select(OrganizationBilling).where(OrganizationBilling.org_id == org_id)
        )
        if billing and billing.billing_email:
            new_value = pii_reencrypt(billing.billing_email)
            if new_value != billing.billing_email:
                billing.billing_email = new_value
                rotated += 1
        invites = list(
            (
                await self.db.execute(
                    select(OrganizationInvite).where(
                        OrganizationInvite.org_id == org_id,
                        OrganizationInvite.accepted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        for invite in invites:
            new_email = pii_reencrypt(invite.email)
            if new_email != invite.email:
                invite.email = new_email
                rotated += 1
        user_ids = [
            row[0]
            for row in (
                await self.db.execute(select(Membership.user_id).where(Membership.org_id == org_id))
            ).all()
        ]
        if user_ids:
            sessions = list(
                (
                    await self.db.execute(
                        select(TokenSession).where(TokenSession.user_id.in_(user_ids))
                    )
                )
                .scalars()
                .all()
            )
            for s in sessions:
                new_ip = pii_reencrypt(s.ip_address)
                new_ua = pii_reencrypt(s.user_agent)
                if new_ip != s.ip_address:
                    s.ip_address = new_ip
                    rotated += 1
                if new_ua != s.user_agent:
                    s.user_agent = new_ua
                    rotated += 1
        await self.audit_repo.log(
            actor_user_id,
            org_id,
            "security.pii.rotate",
            "organization",
            str(org_id),
            {"rotated_fields": rotated, "active_key_id": active_pii_key_id()},
        )
        return {"rotated_fields": rotated, "active_key_id": active_pii_key_id()}

    async def process_due_deletions(self, *, limit: int = 100) -> dict:
        now = utc_now()
        rows = await self.deletion_repo.due_requests(now, limit=limit)
        processed_users = 0
        processed_orgs = 0
        for row in rows:
            if row.scope == "USER" and row.target_user_id:
                if await self._purge_user(row.target_user_id):
                    processed_users += 1
            elif row.scope == "ORG" and row.target_org_id:
                if await self._purge_org(row.target_org_id):
                    processed_orgs += 1
            await self.deletion_repo.mark_processed(row, processed_at=now)
        return {
            "processed_requests": len(rows),
            "users": processed_users,
            "orgs": processed_orgs,
        }

    async def _purge_user(self, user_id: uuid.UUID) -> bool:
        user = await self.db.scalar(select(User).where(User.id == user_id))
        if not user:
            return False
        if user.deleted_at is None:
            user.deleted_at = utc_now()
        user.is_active = False
        user.mfa_enabled = False
        user.mfa_secret_encrypted = None
        user.mfa_recovery_code_hashes = []
        user.email = (
            pii_encrypt(f"deleted+{user.id}@redacted.local") or f"deleted+{user.id}@redacted.local"
        )
        user.password_hash = f"deleted:{secrets.token_hex(16)}"
        sessions = list(
            (await self.db.execute(select(TokenSession).where(TokenSession.user_id == user_id)))
            .scalars()
            .all()
        )
        for s in sessions:
            s.is_revoked = True
            s.ip_address = pii_encrypt(pii_decrypt(s.ip_address) or "redacted")
            s.user_agent = pii_encrypt(pii_decrypt(s.user_agent) or "redacted")
        await self.audit_repo.log(user_id, None, "auth.delete.purged", "user", str(user_id), {})
        return True

    async def _purge_org(self, org_id: uuid.UUID) -> bool:
        org = await self.db.scalar(select(Organization).where(Organization.id == org_id))
        if not org:
            return False
        if org.deleted_at is None:
            org.deleted_at = utc_now()
        org.name = f"Deleted Organization {str(org.id)[:8]}"
        billing = await self.db.scalar(
            select(OrganizationBilling).where(OrganizationBilling.org_id == org_id)
        )
        if billing:
            billing.billing_email = pii_encrypt("redacted@redacted.local")
            billing.billing_notes = None
            billing.customer_id = None
            billing.subscription_id = None
            billing.subscription_status = None
            billing.active_price_id = None
        await self.audit_repo.log(
            None, org_id, "org.delete.purged", "organization", str(org_id), {}
        )
        return True


def decrypt_invite_email(value: str) -> str:
    return pii_decrypt(value) or value
