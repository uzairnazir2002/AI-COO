"""add outbox events table

Revision ID: 0006_outbox_events
Revises: 0005_job_state_lifecycle
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_outbox_events"
down_revision = "0005_job_state_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_status_available", "outbox_events", ["status", "available_at"])
    op.create_index("ix_outbox_org_status_created", "outbox_events", ["org_id", "status", "created_at"])
    op.create_index("ix_outbox_dedupe_key", "outbox_events", ["dedupe_key"], unique=True)
    op.alter_column("outbox_events", "attempts", server_default=None)
    op.alter_column("outbox_events", "max_attempts", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_outbox_dedupe_key", table_name="outbox_events")
    op.drop_index("ix_outbox_org_status_created", table_name="outbox_events")
    op.drop_index("ix_outbox_status_available", table_name="outbox_events")
    op.drop_table("outbox_events")
