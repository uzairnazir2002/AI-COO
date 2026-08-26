import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountConfirmationToken(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "account_confirmation_tokens"
    __table_args__ = (
        Index("ix_account_confirm_token_hash", "token_hash", unique=True),
        Index("ix_account_confirm_code_hash", "code_hash"),
        Index("ix_account_confirm_user_pending", "user_id", "invalidated_at", "used_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    code_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    code_max_attempts: Mapped[int] = mapped_column(default=5, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
