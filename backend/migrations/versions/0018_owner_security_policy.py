"""owner security policy settings

Revision ID: 0018_owner_security_policy
Revises: 0017_idempotency_keys
Create Date: 2026-03-25 00:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0018_owner_security_policy"
down_revision: str | None = "0017_idempotency_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("owner_mfa_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "organization_settings",
        sa.Column("owner_session_max_minutes", sa.Integer(), nullable=False, server_default="120"),
    )
    op.add_column(
        "organization_settings",
        sa.Column("sensitive_action_reauth_minutes", sa.Integer(), nullable=False, server_default="30"),
    )
    op.alter_column("organization_settings", "owner_mfa_required", server_default=None)
    op.alter_column("organization_settings", "owner_session_max_minutes", server_default=None)
    op.alter_column("organization_settings", "sensitive_action_reauth_minutes", server_default=None)


def downgrade() -> None:
    op.drop_column("organization_settings", "sensitive_action_reauth_minutes")
    op.drop_column("organization_settings", "owner_session_max_minutes")
    op.drop_column("organization_settings", "owner_mfa_required")
