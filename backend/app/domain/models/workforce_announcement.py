import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforceAnnouncement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_announcements"
    __table_args__ = (
        Index("ix_workforce_announcement_org_status", "org_id", "status"),
        Index("ix_workforce_announcement_org_published", "org_id", "published_at"),
        Index("ix_workforce_announcement_org_audience", "org_id", "audience_kind"),
        Index("uq_workforce_ann_org_automation_dedupe", "org_id", "automation_dedupe_key", unique=True),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workforce_announcement_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="NORMAL")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledgement_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    audience_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="ORG_ALL")
    audience_ids: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    attachments_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    send_email_on_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    automation_dedupe_key: Mapped[str | None] = mapped_column(String(128), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )
