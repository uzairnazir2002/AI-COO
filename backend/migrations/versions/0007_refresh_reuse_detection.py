"""add token session replacement tracking

Revision ID: 0007_refresh_reuse_detection
Revises: 0006_outbox_events
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_refresh_reuse_detection"
down_revision = "0006_outbox_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("token_sessions", sa.Column("replaced_by_token_hash", sa.String(length=255), nullable=True))
    op.create_index("ix_token_replaced_by_hash", "token_sessions", ["replaced_by_token_hash"])


def downgrade() -> None:
    op.drop_index("ix_token_replaced_by_hash", table_name="token_sessions")
    op.drop_column("token_sessions", "replaced_by_token_hash")
