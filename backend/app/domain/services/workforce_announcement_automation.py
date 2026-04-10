"""Emit org announcements from templates when automation_key matches (payroll, leave, etc.)."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repos.workforce_announcement_repo import WorkforceAnnouncementRepo
from app.domain.repos.workforce_announcement_template_repo import WorkforceAnnouncementTemplateRepo
from app.domain.services.workforce_announcement_service import build_workforce_announcement_service

logger = structlog.get_logger(__name__)

AUTOMATION_KEY_PAYROLL_PERIOD_APPROVED = "PAYROLL_PERIOD_APPROVED"
AUTOMATION_KEY_PAYROLL_PERIOD_PAID = "PAYROLL_PERIOD_PAID"
AUTOMATION_KEY_LEAVE_REQUEST_APPROVED = "LEAVE_REQUEST_APPROVED"
AUTOMATION_KEY_LEAVE_REQUEST_REJECTED = "LEAVE_REQUEST_REJECTED"

AUTOMATION_KEYS_KNOWN = frozenset(
    {
        AUTOMATION_KEY_PAYROLL_PERIOD_APPROVED,
        AUTOMATION_KEY_PAYROLL_PERIOD_PAID,
        AUTOMATION_KEY_LEAVE_REQUEST_APPROVED,
        AUTOMATION_KEY_LEAVE_REQUEST_REJECTED,
    }
)


def _render_template_text(template: str, variables: dict[str, str]) -> str:
    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_Safe({k: str(v) for k, v in variables.items()}))
    except ValueError:
        return template


async def try_emit_automation_announcement(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    automation_key: str,
    dedupe_key: str,
    variables: dict[str, str],
) -> uuid.UUID | None:
    dk = (dedupe_key or "").strip()
    if not dk:
        return None
    ak = (automation_key or "").strip()
    if not ak:
        return None
    try:
        ann_repo = WorkforceAnnouncementRepo(db)
        if await ann_repo.exists_automation_dedupe(org_id=org_id, key=dk):
            return None
        tpl_repo = WorkforceAnnouncementTemplateRepo(db)
        tpl = await tpl_repo.get_active_by_automation_key(org_id=org_id, automation_key=ak)
        if tpl is None:
            return None
        title = _render_template_text(tpl.name, variables)
        body = _render_template_text(tpl.body_template, variables)
        if not title.strip() or not body.strip():
            return None
        svc = build_workforce_announcement_service(db)
        row = await svc.create(
            org_id=org_id,
            actor_user_id=actor_user_id,
            title=title,
            body=body,
            priority="NORMAL",
            pinned=False,
            acknowledgement_required=False,
            expires_at=None,
            scheduled_publish_at=None,
            audience_kind="ORG_ALL",
            audience_ids=None,
            attachments_json=None,
            send_email_on_publish=True,
            template_id=tpl.id,
            automation_dedupe_key=dk[:128],
        )
        published = await svc.publish(org_id=org_id, announcement_id=row.id)
        return published.id
    except Exception:
        logger.exception(
            "workforce_automation_announcement_failed",
            org_id=str(org_id),
            automation_key=ak,
            dedupe_key=dk[:80],
        )
        return None
