from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from app.domain.models.workforce_announcement import WorkforceAnnouncement
from app.domain.models.workforce_announcement_delivery import WorkforceAnnouncementDelivery
from app.domain.models.workforce_announcement_template import WorkforceAnnouncementTemplate
from app.domain.models.workforce_employee import WorkforceEmployee
from app.domain.repos.org_repo import OrgRepo
from app.domain.repos.outbox_repo import OutboxRepo
from app.domain.repos.workforce_announcement_delivery_repo import WorkforceAnnouncementDeliveryRepo
from app.domain.repos.workforce_announcement_repo import WorkforceAnnouncementRepo
from app.domain.repos.workforce_announcement_template_repo import WorkforceAnnouncementTemplateRepo
from app.domain.repos.workforce_employee_repo import WorkforceEmployeeRepo
from app.domain.services.errors import NotFoundError

_AUDIENCE_KINDS = frozenset({"ORG_ALL", "DEPARTMENT", "LOCATION", "TITLE", "MANAGER_TEAM"})


def _parse_uuid_list(raw: list[Any] | None) -> list[uuid.UUID]:
    if not raw:
        return []
    return [uuid.UUID(str(x)) for x in raw]


def _normalize_attachments(raw: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("attachments must be a list")
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each attachment must be an object")
        name = item.get("name")
        url = item.get("url")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("attachment name is required")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("attachment url is required")
        out.append({"name": name.strip(), "url": url.strip()})
    return out


class WorkforceAnnouncementService:
    def __init__(
        self,
        *,
        repo: WorkforceAnnouncementRepo,
        employee_repo: WorkforceEmployeeRepo,
        org_repo: OrgRepo,
        outbox_repo: OutboxRepo,
        delivery_repo: WorkforceAnnouncementDeliveryRepo,
        template_repo: WorkforceAnnouncementTemplateRepo,
    ):
        self.repo = repo
        self.employee_repo = employee_repo
        self.org_repo = org_repo
        self.outbox_repo = outbox_repo
        self.delivery_repo = delivery_repo
        self.template_repo = template_repo

    @staticmethod
    def _can_edit(role: str) -> bool:
        return role in {"OWNER", "EDITOR"}

    def _validate_audience(self, *, kind: str, ids: list[uuid.UUID]) -> tuple[str, list[uuid.UUID] | None]:
        k = (kind or "ORG_ALL").strip().upper()
        if k not in _AUDIENCE_KINDS:
            raise ValueError(f"audience_kind must be one of: {', '.join(sorted(_AUDIENCE_KINDS))}")
        if k == "ORG_ALL":
            return k, None
        if not ids:
            raise ValueError("audience_ids is required for targeted announcements")
        return k, ids

    @staticmethod
    def _visible_to_member(
        row: WorkforceAnnouncement,
        *,
        user_email: str,
        emp: WorkforceEmployee | None,
    ) -> bool:
        kind = (row.audience_kind or "ORG_ALL").strip().upper()
        if kind == "ORG_ALL":
            return True
        if emp is None:
            return False
        raw_ids = row.audience_ids or []
        idset = {str(x) for x in raw_ids}
        if not idset:
            return False
        if kind == "DEPARTMENT":
            return bool(emp.department_id and str(emp.department_id) in idset)
        if kind == "LOCATION":
            return bool(emp.location_id and str(emp.location_id) in idset)
        if kind == "TITLE":
            return bool(emp.title_id and str(emp.title_id) in idset)
        if kind == "MANAGER_TEAM":
            return bool(emp.manager_employee_id and str(emp.manager_employee_id) in idset)
        return False

    async def _email_to_user_map(self, org_id: uuid.UUID) -> dict[str, uuid.UUID]:
        members = await self.org_repo.members(org_id)
        return {u.email.strip().lower(): u.id for _m, u in members if u.email}

    async def _resolve_recipient_emails(
        self,
        *,
        org_id: uuid.UUID,
        row: WorkforceAnnouncement,
    ) -> dict[str, uuid.UUID | None]:
        kind = (row.audience_kind or "ORG_ALL").strip().upper()
        email_map = await self._email_to_user_map(org_id)
        out: dict[str, uuid.UUID | None] = {}
        if kind == "ORG_ALL":
            members = await self.org_repo.members(org_id)
            for _m, u in members:
                if u.email and u.email.strip():
                    em = u.email.strip()
                    out[em] = u.id
            return out
        ids = _parse_uuid_list(list(row.audience_ids or []))
        employees = await self.employee_repo.list_active_for_audience(
            org_id=org_id, audience_kind=kind, audience_ids=ids
        )
        for emp in employees:
            em = (emp.email or "").strip()
            if not em:
                continue
            key = em.lower()
            out[em] = email_map.get(key)
        return out

    async def _enqueue_publish_emails(self, row: WorkforceAnnouncement) -> None:
        if not row.send_email_on_publish:
            return
        recipients = await self._resolve_recipient_emails(org_id=row.org_id, row=row)
        if not recipients:
            return
        subject = f"Announcement: {row.title}"
        body = f"{row.title}\n\n{row.body}"
        for email, user_id in recipients.items():
            delivery = WorkforceAnnouncementDelivery(
                org_id=row.org_id,
                announcement_id=row.id,
                channel="email",
                user_id=user_id,
                recipient_email=email,
                status="PENDING",
            )
            await self.delivery_repo.create(delivery)
            event = await self.outbox_repo.create_event(
                event_type="email.send",
                org_id=row.org_id,
                payload={
                    "to": email,
                    "subject": subject,
                    "body": body,
                    "workforce_announcement_delivery_id": str(delivery.id),
                },
            )
            await self.delivery_repo.attach_outbox(delivery_id=delivery.id, outbox_event_id=event.id)

    async def _ensure_template(self, *, org_id: uuid.UUID, template_id: uuid.UUID | None) -> None:
        if template_id is None:
            return
        tpl = await self.template_repo.get_by_id(org_id=org_id, template_id=template_id)
        if tpl is None:
            raise ValueError("template not found")

    async def list_for_user(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        user_email: str,
        role: str,
        include_archived: bool,
        limit: int = 200,
    ) -> list[WorkforceAnnouncement]:
        _ = user_id
        if self._can_edit(role):
            return await self.repo.list_editor_view(org_id=org_id, include_archived=include_archived, limit=limit)
        emp = await self.employee_repo.get_by_email_ci(org_id=org_id, email=user_email)
        published = await self.repo.list_published_visible(org_id=org_id, as_of=date.today(), limit=limit)
        return [r for r in published if self._visible_to_member(r, user_email=user_email, emp=emp)]

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        title: str,
        body: str,
        priority: str,
        pinned: bool,
        acknowledgement_required: bool,
        expires_at: date | None,
        scheduled_publish_at: datetime | None,
        audience_kind: str = "ORG_ALL",
        audience_ids: list[uuid.UUID] | None = None,
        attachments_json: list[dict[str, Any]] | None = None,
        send_email_on_publish: bool = False,
        template_id: uuid.UUID | None = None,
        automation_dedupe_key: str | None = None,
    ) -> WorkforceAnnouncement:
        t = title.strip()
        b = body.strip()
        if not t:
            raise ValueError("title is required")
        if not b:
            raise ValueError("body is required")
        pr = priority.strip().upper()
        if pr not in {"LOW", "NORMAL", "HIGH"}:
            raise ValueError("priority must be LOW, NORMAL, or HIGH")
        ak, aids = self._validate_audience(kind=audience_kind, ids=list(audience_ids or []))
        att = _normalize_attachments(attachments_json)
        await self._ensure_template(org_id=org_id, template_id=template_id)
        row = WorkforceAnnouncement(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            template_id=template_id,
            title=t,
            body=b,
            priority=pr,
            status="DRAFT",
            published_at=None,
            scheduled_publish_at=scheduled_publish_at,
            expires_at=expires_at,
            pinned=bool(pinned),
            acknowledgement_required=bool(acknowledgement_required),
            audience_kind=ak,
            audience_ids=[str(x) for x in aids] if aids is not None else None,
            attachments_json=att,
            send_email_on_publish=bool(send_email_on_publish),
            automation_dedupe_key=(automation_dedupe_key.strip()[:128] if automation_dedupe_key else None),
        )
        return await self.repo.create(row)

    async def update(
        self,
        *,
        org_id: uuid.UUID,
        announcement_id: uuid.UUID,
        title: str | None = None,
        body: str | None = None,
        priority: str | None = None,
        pinned: bool | None = None,
        acknowledgement_required: bool | None = None,
        expires_at: date | None = None,
        expires_at_clear: bool = False,
        scheduled_publish_at: datetime | None = None,
        scheduled_publish_clear: bool = False,
        audience_kind: str | None = None,
        audience_ids: list[uuid.UUID] | None = None,
        audience_ids_clear: bool = False,
        attachments_json: list[dict[str, Any]] | None = None,
        attachments_clear: bool = False,
        send_email_on_publish: bool | None = None,
        template_id: uuid.UUID | None = None,
        template_clear: bool = False,
    ) -> WorkforceAnnouncement:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        if row.status != "DRAFT":
            raise ValueError("Only draft announcements can be edited")
        if title is not None:
            t = title.strip()
            if not t:
                raise ValueError("title is required")
            row.title = t
        if body is not None:
            b = body.strip()
            if not b:
                raise ValueError("body is required")
            row.body = b
        if priority is not None:
            pr = priority.strip().upper()
            if pr not in {"LOW", "NORMAL", "HIGH"}:
                raise ValueError("priority must be LOW, NORMAL, or HIGH")
            row.priority = pr
        if pinned is not None:
            row.pinned = bool(pinned)
        if acknowledgement_required is not None:
            row.acknowledgement_required = bool(acknowledgement_required)
        if expires_at_clear:
            row.expires_at = None
        elif expires_at is not None:
            row.expires_at = expires_at
        if scheduled_publish_clear:
            row.scheduled_publish_at = None
        elif scheduled_publish_at is not None:
            row.scheduled_publish_at = scheduled_publish_at

        if audience_kind is not None or audience_ids is not None or audience_ids_clear:
            k = (audience_kind if audience_kind is not None else row.audience_kind or "ORG_ALL").strip().upper()
            if audience_ids_clear:
                ids: list[uuid.UUID] = []
            elif audience_ids is not None:
                ids = list(audience_ids)
            else:
                ids = _parse_uuid_list(list(row.audience_ids or []))
            ak, aids = self._validate_audience(kind=k, ids=ids)
            row.audience_kind = ak
            row.audience_ids = [str(x) for x in aids] if aids is not None else None

        if attachments_clear:
            row.attachments_json = None
        elif attachments_json is not None:
            row.attachments_json = _normalize_attachments(attachments_json)

        if send_email_on_publish is not None:
            row.send_email_on_publish = bool(send_email_on_publish)

        if template_clear:
            row.template_id = None
        elif template_id is not None:
            await self._ensure_template(org_id=org_id, template_id=template_id)
            row.template_id = template_id

        return await self.repo.update(row)

    async def publish(
        self,
        *,
        org_id: uuid.UUID,
        announcement_id: uuid.UUID,
    ) -> WorkforceAnnouncement:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        if row.status != "DRAFT":
            raise ValueError("Only draft announcements can be published")
        row.status = "PUBLISHED"
        row.published_at = datetime.now(tz=timezone.utc)
        row.scheduled_publish_at = None
        row = await self.repo.update(row)
        await self._enqueue_publish_emails(row)
        return row

    async def archive(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID) -> WorkforceAnnouncement:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        row.status = "ARCHIVED"
        return await self.repo.update(row)

    async def get_and_mark_read(
        self,
        *,
        org_id: uuid.UUID,
        announcement_id: uuid.UUID,
        user_id: uuid.UUID,
        user_email: str,
        role: str,
    ) -> tuple[WorkforceAnnouncement, object | None]:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        if not self._can_edit(role):
            if row.status != "PUBLISHED":
                raise NotFoundError("Announcement not found")
            if row.expires_at is not None and row.expires_at < date.today():
                raise NotFoundError("Announcement not found")
            emp = await self.employee_repo.get_by_email_ci(org_id=org_id, email=user_email)
            if not self._visible_to_member(row, user_email=user_email, emp=emp):
                raise NotFoundError("Announcement not found")
        receipt = await self.repo.upsert_receipt_read(announcement_id=announcement_id, user_id=user_id)
        return row, receipt

    async def acknowledge(self, *, org_id: uuid.UUID, announcement_id: uuid.UUID, user_id: uuid.UUID, user_email: str) -> object:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        if row.status != "PUBLISHED":
            raise ValueError("Announcement is not published")
        if not row.acknowledgement_required:
            raise ValueError("Acknowledgement is not required for this announcement")
        emp = await self.employee_repo.get_by_email_ci(org_id=org_id, email=user_email)
        if not self._visible_to_member(row, user_email=user_email, emp=emp):
            raise NotFoundError("Announcement not found")
        return await self.repo.upsert_receipt_ack(announcement_id=announcement_id, user_id=user_id)

    async def list_deliveries_page(
        self,
        *,
        org_id: uuid.UUID,
        announcement_id: uuid.UUID,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list, int]:
        row = await self.repo.get_by_id(org_id=org_id, announcement_id=announcement_id)
        if row is None:
            raise NotFoundError("Announcement not found")
        return await self.delivery_repo.list_for_announcement_page(
            org_id=org_id,
            announcement_id=announcement_id,
            status=status,
            page=page,
            page_size=page_size,
        )


class WorkforceAnnouncementTemplateService:
    def __init__(self, *, repo: WorkforceAnnouncementTemplateRepo):
        self.repo = repo

    async def list_templates(self, *, org_id: uuid.UUID, include_inactive: bool = False) -> list[WorkforceAnnouncementTemplate]:
        return await self.repo.list_by_org(org_id=org_id, include_inactive=include_inactive)

    async def create(
        self,
        *,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        body_template: str,
        code: str | None = None,
        description: str | None = None,
        automation_key: str | None = None,
    ) -> WorkforceAnnouncementTemplate:
        n = name.strip()
        b = body_template.strip()
        if not n:
            raise ValueError("name is required")
        if not b:
            raise ValueError("body_template is required")
        c = (code or "").strip() or None
        if c:
            existing = await self.repo.get_by_code(org_id=org_id, code=c)
            if existing is not None:
                raise ValueError("template code already exists")
        row = WorkforceAnnouncementTemplate(
            org_id=org_id,
            created_by_user_id=actor_user_id,
            name=n,
            code=c,
            description=(description or "").strip() or None,
            body_template=b,
            automation_key=(automation_key or "").strip() or None,
            is_active=True,
        )
        return await self.repo.create(row)

    async def update(
        self,
        *,
        org_id: uuid.UUID,
        template_id: uuid.UUID,
        name: str | None = None,
        body_template: str | None = None,
        code: str | None = None,
        code_clear: bool = False,
        description: str | None = None,
        description_clear: bool = False,
        automation_key: str | None = None,
        automation_clear: bool = False,
        is_active: bool | None = None,
    ) -> WorkforceAnnouncementTemplate:
        row = await self.repo.get_by_id(org_id=org_id, template_id=template_id)
        if row is None:
            raise NotFoundError("Template not found")
        if name is not None:
            n = name.strip()
            if not n:
                raise ValueError("name is required")
            row.name = n
        if body_template is not None:
            b = body_template.strip()
            if not b:
                raise ValueError("body_template is required")
            row.body_template = b
        if code_clear:
            row.code = None
        elif code is not None:
            c = code.strip() or None
            if c:
                existing = await self.repo.get_by_code(org_id=org_id, code=c)
                if existing is not None and existing.id != row.id:
                    raise ValueError("template code already exists")
            row.code = c
        if description_clear:
            row.description = None
        elif description is not None:
            row.description = description.strip() or None
        if automation_clear:
            row.automation_key = None
        elif automation_key is not None:
            row.automation_key = automation_key.strip() or None
        if is_active is not None:
            row.is_active = bool(is_active)
        return await self.repo.update(row)


def build_workforce_announcement_service(db) -> WorkforceAnnouncementService:
    return WorkforceAnnouncementService(
        repo=WorkforceAnnouncementRepo(db),
        employee_repo=WorkforceEmployeeRepo(db),
        org_repo=OrgRepo(db),
        outbox_repo=OutboxRepo(db),
        delivery_repo=WorkforceAnnouncementDeliveryRepo(db),
        template_repo=WorkforceAnnouncementTemplateRepo(db),
    )


def build_workforce_announcement_template_service(db) -> WorkforceAnnouncementTemplateService:
    return WorkforceAnnouncementTemplateService(repo=WorkforceAnnouncementTemplateRepo(db))
