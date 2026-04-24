from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.domain.models.workforce_checklist_item import WorkforceChecklistItem
from app.domain.models.workforce_document import WorkforceDocument
from app.domain.models.workforce_policy import WorkforcePolicy
from app.domain.models.workforce_policy_ack import WorkforcePolicyAcknowledgement
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.repos.workforce_hr_repo import WorkforceHrRepo
from app.domain.services.errors import NotFoundError


VALID_CHECKLIST_KINDS = {"ONBOARDING", "OFFBOARDING"}


class WorkforceHrService:
    def __init__(self, *, hr_repo: WorkforceHrRepo, employee_repo: WorkforceEmployeeRepo):
        self.hr_repo = hr_repo
        self.employee_repo = employee_repo

    @staticmethod
    def _normalize_code(code: str) -> str:
        c = (code or "").strip().upper()
        if not c:
            raise ValueError("Code is required")
        if len(c) > 64:
            raise ValueError("Code too long")
        return c

    @staticmethod
    def _normalize_title(value: str, label: str = "Title") -> str:
        v = (value or "").strip()
        if not v:
            raise ValueError(f"{label} is required")
        return v

    @staticmethod
    def _normalize_kind(kind: str) -> str:
        k = (kind or "").strip().upper()
        if k not in VALID_CHECKLIST_KINDS:
            raise ValueError("Unsupported checklist kind")
        return k

    # Policies
    async def list_policies(self, *, org_id: uuid.UUID, include_inactive: bool, limit: int = 200) -> list[WorkforcePolicy]:
        return await self.hr_repo.list_policies(org_id=org_id, include_inactive=include_inactive, limit=limit)

    async def create_policy(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        code: str,
        title: str,
        body: str,
        requires_ack: bool,
        publish_now: bool,
        is_active: bool = True,
    ) -> WorkforcePolicy:
        normalized_code = self._normalize_code(code)
        normalized_title = self._normalize_title(title, "Policy title")
        normalized_body = (body or "").strip()
        if not normalized_body:
            raise ValueError("Policy body is required")
        row = WorkforcePolicy(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            code=normalized_code,
            title=normalized_title,
            body=normalized_body,
            version=1,
            requires_ack=bool(requires_ack),
            is_active=bool(is_active),
            published_at=(datetime.now(tz=timezone.utc) if publish_now else None),
        )
        return await self.hr_repo.create_policy(row)

    async def publish_policy(self, *, org_id: uuid.UUID, policy_id: uuid.UUID) -> WorkforcePolicy:
        row = await self.hr_repo.get_policy(org_id=org_id, policy_id=policy_id)
        if row is None:
            raise NotFoundError("Policy not found")
        if not row.is_active:
            raise ValueError("Cannot publish an inactive policy")
        row.published_at = datetime.now(tz=timezone.utc)
        row.version = int(row.version) + 1
        await self.hr_repo.db.flush()
        return row

    async def acknowledge_policy_for_employee(
        self, *, org_id: uuid.UUID, policy_id: uuid.UUID, employee_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> WorkforcePolicyAcknowledgement:
        policy = await self.hr_repo.get_policy(org_id=org_id, policy_id=policy_id)
        if policy is None or not policy.is_active:
            raise NotFoundError("Policy not found")
        employee = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if employee is None or not employee.is_active:
            raise NotFoundError("Employee not found")
        ack = WorkforcePolicyAcknowledgement(
            org_id=org_id,
            policy_id=policy_id,
            employee_id=employee_id,
            acknowledged_by_user_id=actor_user_id,
            acknowledged_at=datetime.now(tz=timezone.utc),
        )
        return await self.hr_repo.upsert_ack(ack)

    async def list_policy_acks(self, *, org_id: uuid.UUID, policy_id: uuid.UUID, limit: int = 5000) -> list[WorkforcePolicyAcknowledgement]:
        policy = await self.hr_repo.get_policy(org_id=org_id, policy_id=policy_id)
        if policy is None:
            raise NotFoundError("Policy not found")
        return await self.hr_repo.list_policy_acks(org_id=org_id, policy_id=policy_id, limit=limit)

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
        if employee_id is not None:
            employee = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
            if employee is None:
                raise NotFoundError("Employee not found")
        if policy_id is not None:
            policy = await self.hr_repo.get_policy(org_id=org_id, policy_id=policy_id)
            if policy is None:
                raise NotFoundError("Policy not found")
        return await self.hr_repo.list_documents(
            org_id=org_id,
            employee_id=employee_id,
            policy_id=policy_id,
            include_inactive=include_inactive,
            limit=limit,
        )

    async def create_document(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID | None,
        policy_id: uuid.UUID | None,
        name: str,
        content_type: str,
        size_bytes: int,
        object_key: str,
        url: str,
    ) -> WorkforceDocument:
        if employee_id is None and policy_id is None:
            raise ValueError("Document must be attached to an employee or a policy")
        if employee_id is not None:
            employee = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
            if employee is None:
                raise NotFoundError("Employee not found")
        if policy_id is not None:
            policy = await self.hr_repo.get_policy(org_id=org_id, policy_id=policy_id)
            if policy is None:
                raise NotFoundError("Policy not found")
        clean_name = (name or "").strip()
        if not clean_name:
            raise ValueError("Document name is required")
        if len(clean_name) > 200:
            raise ValueError("Document name too long")
        ct = (content_type or "").strip().lower()
        if not ct:
            raise ValueError("Content type is required")
        if size_bytes < 0:
            raise ValueError("Invalid size")
        ok = (object_key or "").strip()
        if not ok:
            raise ValueError("Missing object key")
        u = (url or "").strip()
        if not u:
            raise ValueError("Missing URL")
        row = WorkforceDocument(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            employee_id=employee_id,
            policy_id=policy_id,
            name=clean_name,
            content_type=ct,
            size_bytes=int(size_bytes),
            object_key=ok,
            url=u,
            is_active=True,
        )
        return await self.hr_repo.create_document(row)

    async def deactivate_document(self, *, org_id: uuid.UUID, document_id: uuid.UUID) -> WorkforceDocument:
        row = await self.hr_repo.deactivate_document(org_id=org_id, document_id=document_id)
        if row is None:
            raise NotFoundError("Document not found")
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
        normalized_kind = self._normalize_kind(kind) if kind is not None else None
        if employee_id is not None:
            employee = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
            if employee is None:
                raise NotFoundError("Employee not found")
        return await self.hr_repo.list_checklist(
            org_id=org_id,
            employee_id=employee_id,
            kind=normalized_kind,
            include_done=include_done,
            limit=limit,
        )

    async def create_checklist_item(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        employee_id: uuid.UUID,
        kind: str,
        title: str,
        details: str | None,
        due_date: date | None,
    ) -> WorkforceChecklistItem:
        employee = await self.employee_repo.get_by_id(org_id=org_id, employee_id=employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        normalized_kind = self._normalize_kind(kind)
        normalized_title = self._normalize_title(title, "Checklist title")
        d = (details or "").strip() or None
        if d and len(d) > 1000:
            raise ValueError("Details too long")
        row = WorkforceChecklistItem(
            org_id=org_id,
            employee_id=employee_id,
            kind=normalized_kind,
            title=normalized_title,
            details=d,
            due_date=due_date,
            is_done=False,
            completed_at=None,
            completed_by_user_id=None,
        )
        return await self.hr_repo.create_checklist_item(row)

    async def set_checklist_done(
        self, *, org_id: uuid.UUID, item_id: uuid.UUID, done: bool, actor_user_id: uuid.UUID
    ) -> WorkforceChecklistItem:
        now = datetime.now(tz=timezone.utc)
        row = await self.hr_repo.set_checklist_done(
            org_id=org_id,
            item_id=item_id,
            done=bool(done),
            by_user_id=(actor_user_id if done else None),
            at=(now if done else None),
        )
        if row is None:
            raise NotFoundError("Checklist item not found")
        return row

