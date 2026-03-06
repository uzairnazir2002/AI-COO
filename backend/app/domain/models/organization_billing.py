import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationBilling(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_billing"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        unique=True,
    )
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_label: Mapped[str] = mapped_column(String(64), nullable=False, default="FREE")
    billing_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subscription_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_price_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(tz=timezone.utc),
    )
