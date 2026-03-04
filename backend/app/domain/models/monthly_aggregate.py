import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import UUIDPrimaryKeyMixin


class MonthlyAggregate(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "monthly_aggregates"
    __table_args__ = (UniqueConstraint("org_id", "year_month", name="uq_agg_org_month"),)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    year_month: Mapped[date] = mapped_column(Date, nullable=False)
    revenue_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    expense_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=timezone.utc), nullable=False
    )
