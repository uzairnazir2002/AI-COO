import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PaymentProcessorConnection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_processor_connections"
    __table_args__ = (
        UniqueConstraint("org_id", "provider", name="uq_payment_conn_org_provider"),
        Index("ix_payment_conn_org_provider_status", "org_id", "provider", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(24), nullable=False, default="STRIPE")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ACTIVE")
    provider_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
