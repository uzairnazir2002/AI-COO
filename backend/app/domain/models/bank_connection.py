import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BankConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bank_connections"
    __table_args__ = (
        UniqueConstraint("org_id", "provider", "external_item_id", name="uq_bank_conn_org_provider_item"),
        Index("ix_bank_conn_org_status", "org_id", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False, default="PLAID")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    external_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
    )
