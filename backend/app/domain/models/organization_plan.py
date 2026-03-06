import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_plans"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        unique=True,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False, default="FREE")
    transaction_limit_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    report_limit_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    ai_summary_limit_monthly: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
