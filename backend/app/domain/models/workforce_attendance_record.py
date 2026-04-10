import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforceAttendanceRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_attendance_records"
    __table_args__ = (
        UniqueConstraint("org_id", "employee_id", "work_date", name="uq_workforce_attendance_org_emp_date"),
        Index("ix_workforce_attendance_org_date", "org_id", "work_date"),
        Index("ix_workforce_attendance_org_employee_date", "org_id", "employee_id", "work_date"),
        Index("ix_workforce_attendance_org_status_date", "org_id", "status", "work_date"),
        Index("ix_workforce_attendance_org_flags", "org_id", "is_late", "missing_checkout"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PRESENT")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="CLOCK")

    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_shifts.id", ondelete="SET NULL"), nullable=True
    )
    shift_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_shift_assignments.id", ondelete="SET NULL"), nullable=True
    )

    clock_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_late: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    minutes_late: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_checkout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    worked_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payable_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))

    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

