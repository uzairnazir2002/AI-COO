import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import UUIDPrimaryKeyMixin


class Forecast(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "forecasts"
    __table_args__ = (
        UniqueConstraint("org_id", "month", "scenario", name="uq_forecast_org_month_scenario"),
        Index("ix_forecast_org_month", "org_id", "month"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False)
    scenario: Mapped[str] = mapped_column(String(16), nullable=False)
    revenue_pred: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expense_pred: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    confidence_low: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    confidence_high: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False
    )
    overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
