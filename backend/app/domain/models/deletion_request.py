import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeletionRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        Index("ix_deletion_requests_due", "status", "delete_after"),
        Index("ix_deletion_requests_scope", "scope", "target_user_id", "target_org_id"),
    )

    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # USER | ORG
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")  # PENDING | PROCESSED | CANCELLED
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delete_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
