"""add partial index for open alerts

Revision ID: 0008_alerts_open_partial_index
Revises: 0007_refresh_reuse_detection
Create Date: 2026-03-05
"""

from alembic import op


revision = "0008_alerts_open_partial_index"
down_revision = "0007_refresh_reuse_detection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alerts_open_org_created "
        "ON alerts (org_id, created_at DESC) WHERE status = 'OPEN'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alerts_open_org_created")
