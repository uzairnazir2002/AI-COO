"""workforce policy ack updated_at default

Revision ID: 0038_workforce_policy_ack_updated_at_default
Revises: 0037_workforce_hr_admin_phase6
Create Date: 2026-04-23 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_workforce_policy_ack_updated_at_default"
down_revision: str | None = "0037_workforce_hr_admin_phase6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE workforce_policy_acknowledgements
            SET updated_at = COALESCE(updated_at, created_at)
            WHERE updated_at IS NULL
            """
        )
    )
    op.alter_column(
        "workforce_policy_acknowledgements",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "workforce_policy_acknowledgements",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=None,
    )

