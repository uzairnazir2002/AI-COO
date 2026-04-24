import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforceEmployee(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_employees"
    __table_args__ = (
        UniqueConstraint("org_id", "employee_code", name="uq_workforce_employee_org_code"),
        Index("ix_workforce_employee_org_active", "org_id", "is_active"),
        Index("ix_workforce_employee_org_department", "org_id", "department_id"),
        Index("ix_workforce_employee_org_title", "org_id", "title_id"),
        Index("ix_workforce_employee_org_manager", "org_id", "manager_employee_id"),
        Index("ix_workforce_employee_org_location", "org_id", "location_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    employee_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_departments.id", ondelete="SET NULL"), nullable=True
    )
    title_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_titles.id", ondelete="SET NULL"), nullable=True
    )
    manager_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="SET NULL"), nullable=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )

    employment_type: Mapped[str] = mapped_column(String(16), nullable=False, default="FULL_TIME")
    employment_status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    contract_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    probation_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    salary_type: Mapped[str] = mapped_column(String(16), nullable=False, default="SALARIED")
    base_salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

