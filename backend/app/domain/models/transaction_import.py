import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TransactionImport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "transaction_imports"
    __table_args__ = (
        Index("ix_tx_import_org_created", "org_id", "created_at"),
        Index("ix_tx_import_org_status", "org_id", "status"),
        Index("ix_tx_import_profile", "mapping_profile_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mapping_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_mapping_profiles.id"), nullable=True
    )
    mapping_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_rows_json: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
