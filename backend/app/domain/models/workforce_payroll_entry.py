import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforcePayrollEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_payroll_entries"
    __table_args__ = (
        UniqueConstraint("org_id", "payroll_period_id", "employee_id", name="uq_workforce_payroll_entry_org_period_emp"),
        Index("ix_workforce_payroll_entry_org_period", "org_id", "payroll_period_id"),
        Index("ix_workforce_payroll_entry_org_employee", "org_id", "employee_id"),
        Index("ix_workforce_payroll_entry_org_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    payroll_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_payroll_periods.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=False
    )

    # Snapshot compensation mode at generation time.
    salary_type: Mapped[str] = mapped_column(String(16), nullable=False, default="SALARIED")  # SALARIED/HOURLY
    base_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    overtime_multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("1.5"))

    worked_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payable_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))

    # Approved unpaid leave (is_paid=false) overlapping the payroll period; salaried gross = base_salary - this.
    unpaid_leave_deduction: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))

    gross_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    adjustments_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    net_pay: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")  # DRAFT/APPROVED/PAID
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

