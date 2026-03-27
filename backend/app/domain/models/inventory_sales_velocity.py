import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import UUIDPrimaryKeyMixin


class InventorySalesVelocity(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "inventory_sales_velocity"
    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "item_id",
            "location_id",
            "window_days",
            name="uq_inventory_sales_velocity_org_item_location_window",
        ),
        Index("ix_inventory_sales_velocity_org_item", "org_id", "item_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True
    )
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    units_per_day: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    basis_start: Mapped[date] = mapped_column(Date, nullable=False)
    basis_end: Mapped[date] = mapped_column(Date, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=timezone.utc)
    )
