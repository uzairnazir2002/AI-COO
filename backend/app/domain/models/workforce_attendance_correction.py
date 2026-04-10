import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforceAttendanceCorrection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_attendance_corrections"
    __table_args__ = (
        Index("ix_workforce_att_corr_org_status", "org_id", "status"),
        Index("ix_workforce_att_corr_org_employee", "org_id", "employee_id"),
        Index("ix_workforce_att_corr_org_record", "org_id", "attendance_record_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=False
    )
    attendance_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_attendance_records.id", ondelete="CASCADE"), nullable=False
    )

    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    reason: Mapped[str] = mapped_column(String(500), nullable=False)

    proposed_clock_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposed_clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proposed_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

