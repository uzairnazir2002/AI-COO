import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforcePolicyAcknowledgement(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_policy_acknowledgements"
    __table_args__ = (
        UniqueConstraint("org_id", "policy_id", "employee_id", name="uq_workforce_policy_ack_org_policy_emp"),
        Index("ix_workforce_policy_ack_org_policy", "org_id", "policy_id"),
        Index("ix_workforce_policy_ack_org_employee", "org_id", "employee_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_policies.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=False
    )

    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc)
    )
    acknowledged_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

