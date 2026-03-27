"""mfa recovery codes

Revision ID: 0016_mfa_recovery_codes
Revises: 0015_mfa_sessions
Create Date: 2026-03-24 22:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0016_mfa_recovery_codes"
down_revision: str | None = "0015_mfa_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mfa_recovery_code_hashes", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.alter_column("users", "mfa_recovery_code_hashes", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "mfa_recovery_code_hashes")
