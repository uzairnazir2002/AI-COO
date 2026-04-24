from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.workforce_checklist_item import WorkforceChecklistItem
from app.domain.models.workforce_document import WorkforceDocument
from app.domain.models.workforce_policy import WorkforcePolicy
from app.domain.models.workforce_policy_ack import WorkforcePolicyAcknowledgement


class WorkforceHrRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Policies
    async def list_policies(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int = 200) -> list[WorkforcePolicy]:
        q = select(WorkforcePolicy).where(WorkforcePolicy.org_id == org_id)
        if not include_inactive:
            q = q.where(WorkforcePolicy.is_active.is_(True))
        q = q.order_by(desc(WorkforcePolicy.published_at), desc(WorkforcePolicy.updated_at)).limit(max(1, min(limit, 500)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_policy(self, *, org_id: uuid.UUID, policy_id: uuid.UUID) -> WorkforcePolicy | None:
        rows = await self.db.execute(
            select(WorkforcePolicy).where(WorkforcePolicy.org_id == org_id, WorkforcePolicy.id == policy_id)
        )
        return rows.scalar_one_or_none()

    async def create_policy(self, row: WorkforcePolicy) -> WorkforcePolicy:
        self.db.add(row)
        await self.db.flush()
        return row

    async def list_policy_acks(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, limit: int = 5000) -> list[WorkforcePolicyAcknowledgement]:
        q = (
            select(WorkforcePolicyAcknowledgement)
            .where(WorkforcePolicyAcknowledgement.org_id == org_id, WorkforcePolicyAcknowledgement.policy_id == policy_id)
            .order_by(desc(WorkforcePolicyAcknowledgement.acknowledged_at))
            .limit(max(1, min(limit, 10000)))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_ack(
        self, *, org_id: uuid.UUID, policy_id: uuid.UUID, employee_id: uuid.UUID
    ) -> WorkforcePolicyAcknowledgement | None:
        rows = await self.db.execute(
            select(WorkforcePolicyAcknowledgement).where(
                WorkforcePolicyAcknowledgement.org_id == org_id,
                WorkforcePolicyAcknowledgement.policy_id == policy_id,
                WorkforcePolicyAcknowledgement.employee_id == employee_id,
            )
        )
        return rows.scalar_one_or_none()

    async def upsert_ack(self, row: WorkforcePolicyAcknowledgement) -> WorkforcePolicyAcknowledgement:
        existing = await self.get_ack(org_id=row.org_id, policy_id=row.policy_id, employee_id=row.employee_id)
        if existing:
            existing.acknowledged_at = row.acknowledged_at
            existing.acknowledged_by_user_id = row.acknowledged_by_user_id
            await self.db.flush()
            return existing
        self.db.add(row)
        await self.db.flush()
        return row

    # Documents
    async def list_documents(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        policy_id: uuid.UUID | None,
        include_inactive: bool,
        limit: int = 500,
    ) -> list[WorkforceDocument]:
        q = select(WorkforceDocument).where(WorkforceDocument.org_id == org_id)
        if not include_inactive:
            q = q.where(WorkforceDocument.is_active.is_(True))
        if employee_id is not None:
            q = q.where(WorkforceDocument.employee_id == employee_id)
        if policy_id is not None:
            q = q.where(WorkforceDocument.policy_id == policy_id)
        q = q.order_by(desc(WorkforceDocument.created_at)).limit(max(1, min(limit, 2000)))
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def create_document(self, row: WorkforceDocument) -> WorkforceDocument:
        self.db.add(row)
        await self.db.flush()
        return row

    async def deactivate_document(self, *, org_id: uuid.UUID, document_id: uuid.UUID) -> WorkforceDocument | None:
        rows = await self.db.execute(
            select(WorkforceDocument).where(WorkforceDocument.org_id == org_id, WorkforceDocument.id == document_id)
        )
        row = rows.scalar_one_or_none()
        if not row:
            return None
        row.is_active = False
        await self.db.flush()
        return row

    # Checklist
    async def list_checklist(
        self,
        *,
        org_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        kind: str | None,
        include_done: bool,
        limit: int = 5000,
    ) -> list[WorkforceChecklistItem]:
        q = select(WorkforceChecklistItem).where(WorkforceChecklistItem.org_id == org_id)
        if employee_id is not None:
            q = q.where(WorkforceChecklistItem.employee_id == employee_id)
        if kind is not None:
            q = q.where(WorkforceChecklistItem.kind == kind)
        if not include_done:
            q = q.where(WorkforceChecklistItem.is_done.is_(False))
        q = q.order_by(desc(WorkforceChecklistItem.due_date), desc(WorkforceChecklistItem.created_at)).limit(
            max(1, min(limit, 10000))
        )
        rows = await self.db.execute(q)
        return list(rows.scalars().all())

    async def get_checklist_item(self, *, org_id: uuid.UUID, item_id: uuid.UUID) -> WorkforceChecklistItem | None:
        rows = await self.db.execute(
            select(WorkforceChecklistItem).where(WorkforceChecklistItem.org_id == org_id, WorkforceChecklistItem.id == item_id)
        )
        return rows.scalar_one_or_none()

    async def create_checklist_item(self, row: WorkforceChecklistItem) -> WorkforceChecklistItem:
        self.db.add(row)
        await self.db.flush()
        return row

    async def set_checklist_done(
        self, *, org_id: uuid.UUID, item_id: uuid.UUID, done: bool, by_user_id: uuid.UUID | None, at: datetime | None
    ) -> WorkforceChecklistItem | None:
        row = await self.get_checklist_item(org_id=org_id, item_id=item_id)
        if not row:
            return None
        row.is_done = bool(done)
        row.completed_by_user_id = by_user_id if done else None
        row.completed_at = at if done else None
        await self.db.flush()
        return row

