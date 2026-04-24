import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforceChecklistItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_checklist_items"
    __table_args__ = (
        Index("ix_workforce_checklist_org_employee", "org_id", "employee_id"),
        Index("ix_workforce_checklist_org_kind", "org_id", "kind"),
        Index("ix_workforce_checklist_org_kind_done", "org_id", "kind", "is_done"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=False
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # ONBOARDING | OFFBOARDING
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

