import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_settings"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), unique=True, nullable=False
    )
    starting_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    runway_alert_threshold_days: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    vendor_concentration_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("50.00"), nullable=False
    )
    budget_variance_alert_threshold_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("10.00"), nullable=False
    )
    misc_growth_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.40"), nullable=False
    )
    anomaly_spike_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("1.50"), nullable=False
    )
    owner_mfa_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    owner_session_max_minutes: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    sensitive_action_reauth_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
