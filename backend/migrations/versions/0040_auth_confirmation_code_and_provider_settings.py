"""auth confirmation code fields and email provider settings

Revision ID: 0040_auth_confirmation_code_and_provider_settings
Revises: 0039_org_settings_workforce_canonical_flag
Create Date: 2026-05-21 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0040_auth_confirmation_code_and_provider_settings"
down_revision: str | None = "0039_org_settings_workforce_canonical_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("account_confirmation_tokens", sa.Column("code_hash", sa.String(length=255), nullable=True))
    op.add_column("account_confirmation_tokens", sa.Column("code_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "account_confirmation_tokens",
        sa.Column("code_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "account_confirmation_tokens",
        sa.Column("code_max_attempts", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column("account_confirmation_tokens", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_account_confirm_code_hash", "account_confirmation_tokens", ["code_hash"], unique=False)
    op.create_index(
        "ix_account_confirm_user_pending",
        "account_confirmation_tokens",
        ["user_id", "invalidated_at", "used_at", "expires_at"],
        unique=False,
    )
    op.alter_column("account_confirmation_tokens", "code_attempts", server_default=None)
    op.alter_column("account_confirmation_tokens", "code_max_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_account_confirm_user_pending", table_name="account_confirmation_tokens")
    op.drop_index("ix_account_confirm_code_hash", table_name="account_confirmation_tokens")
    op.drop_column("account_confirmation_tokens", "invalidated_at")
    op.drop_column("account_confirmation_tokens", "code_max_attempts")
    op.drop_column("account_confirmation_tokens", "code_attempts")
    op.drop_column("account_confirmation_tokens", "code_expires_at")
    op.drop_column("account_confirmation_tokens", "code_hash")
