import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.category import Category
from app.domain.models.membership import Membership
from app.domain.models.organization import Organization
from app.domain.models.organization_billing import OrganizationBilling
from app.domain.models.organization_invite import OrganizationInvite
from app.domain.models.organization_plan import OrganizationPlan
from app.domain.models.organization_setting import OrganizationSetting
from app.domain.models.user import User
from app.core.pii_crypto import pii_encrypt


class OrgRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_org(self, name: str) -> Organization:
        org = Organization(name=name)
        self.db.add(org)
        await self.db.flush()
        self.db.add(OrganizationSetting(org_id=org.id, starting_cash=0))
        self.db.add(
            OrganizationBilling(
                org_id=org.id,
                billing_email=None,
                invoice_enabled=False,
                plan_label="FREE",
                billing_notes=None,
            )
        )
        self.db.add(
            OrganizationPlan(
                org_id=org.id,
                code="FREE",
                transaction_limit_monthly=10000,
                report_limit_monthly=20,
                ai_summary_limit_monthly=500,
            )
        )
        defaults = [
            ("Sales", "REVENUE"),
            ("Services", "REVENUE"),
            ("Payroll", "EXPENSE"),
            ("Rent", "EXPENSE"),
            ("Marketing", "EXPENSE"),
            ("Misc", "EXPENSE"),
        ]
        for n, t in defaults:
            self.db.add(Category(org_id=org.id, name=n, type=t, is_default=True))
        await self.db.flush()
        return org

    async def add_membership(self, user_id: uuid.UUID, org_id: uuid.UUID, role: str) -> Membership:
        m = Membership(user_id=user_id, org_id=org_id, role=role)
        self.db.add(m)
        await self.db.flush()
        return m

    async def list_orgs_for_user(self, user_id: uuid.UUID) -> list[tuple[Organization, Membership]]:
        q = await self.db.execute(
            select(Organization, Membership)
            .join(Membership, Membership.org_id == Organization.id)
            .where(Membership.user_id == user_id, Organization.deleted_at.is_(None))
        )
        return list(q.all())

    async def membership(self, user_id: uuid.UUID, org_id: uuid.UUID) -> Membership | None:
        q = await self.db.execute(
            select(Membership)
            .join(Organization, Organization.id == Membership.org_id)
            .where(Membership.user_id == user_id, Membership.org_id == org_id, Organization.deleted_at.is_(None))
        )
        return q.scalar_one_or_none()

    async def owner_org_ids_requiring_mfa(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        q = await self.db.execute(
            select(OrganizationSetting.org_id)
            .join(Membership, Membership.org_id == OrganizationSetting.org_id)
            .where(
                Membership.user_id == user_id,
                Membership.role == "OWNER",
                OrganizationSetting.owner_mfa_required.is_(True),
            )
        )
        return list(q.scalars().all())

    async def members(self, org_id: uuid.UUID) -> list[tuple[Membership, User]]:
        q = await self.db.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.org_id == org_id, User.deleted_at.is_(None))
        )
        return list(q.all())

    async def get_settings(self, org_id: uuid.UUID) -> OrganizationSetting | None:
        q = await self.db.execute(select(OrganizationSetting).where(OrganizationSetting.org_id == org_id))
        return q.scalar_one_or_none()

    async def save_settings(self, settings: OrganizationSetting) -> OrganizationSetting:
        self.db.add(settings)
        await self.db.flush()
        return settings

    async def get_billing(self, org_id: uuid.UUID) -> OrganizationBilling | None:
        q = await self.db.execute(select(OrganizationBilling).where(OrganizationBilling.org_id == org_id))
        return q.scalar_one_or_none()

    async def get_billing_by_customer_id(self, customer_id: str) -> OrganizationBilling | None:
        q = await self.db.execute(select(OrganizationBilling).where(OrganizationBilling.customer_id == customer_id))
        return q.scalar_one_or_none()

    async def save_billing(self, billing: OrganizationBilling) -> OrganizationBilling:
        self.db.add(billing)
        await self.db.flush()
        return billing

    async def get_org(self, org_id: uuid.UUID) -> Organization | None:
        q = await self.db.execute(select(Organization).where(Organization.id == org_id, Organization.deleted_at.is_(None)))
        return q.scalar_one_or_none()

    async def create_invite(
        self,
        org_id: uuid.UUID,
        email: str,
        role: str,
        invited_by: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> OrganizationInvite:
        invite = OrganizationInvite(
            org_id=org_id,
            email=pii_encrypt(email.lower()) or email.lower(),
            role=role,
            invited_by=invited_by,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(invite)
        await self.db.flush()
        return invite

    async def get_invite_by_hash(self, token_hash: str) -> OrganizationInvite | None:
        q = await self.db.execute(
            select(OrganizationInvite).where(OrganizationInvite.token_hash == token_hash)
        )
        return q.scalar_one_or_none()
