import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class WorkforcePolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workforce_policies"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_workforce_policy_org_code"),
        Index("ix_workforce_policy_org_active", "org_id", "is_active"),
        Index("ix_workforce_policy_org_published", "org_id", "published_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)

    requires_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )

