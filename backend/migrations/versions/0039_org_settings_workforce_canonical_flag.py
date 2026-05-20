"""org settings workforce canonical flag

Revision ID: 0039_org_settings_workforce_canonical_flag
Revises: 0038_workforce_policy_ack_updated_at_default
Create Date: 2026-05-05 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039_org_settings_workforce_canonical_flag"
down_revision: str | None = "0038_workforce_policy_ack_updated_at_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("workforce_org_context_canonical", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("organization_settings", "workforce_org_context_canonical", server_default=None)


def downgrade() -> None:
    op.drop_column("organization_settings", "workforce_org_context_canonical")
