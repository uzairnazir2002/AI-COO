"""dead letter events

Revision ID: 0020_dead_letter_events
Revises: 0019_privacy_and_deletion_baseline
Create Date: 2026-03-25 23:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0020_dead_letter_events"
down_revision: str | None = "0019_privacy_and_deletion_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dead_letter_events",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_task_id", sa.String(length=100), nullable=True),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("first_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dead_letter_org_status_created",
        "dead_letter_events",
        ["org_id", "status", "created_at"],
        unique=False,
    )
    op.create_index("ix_dead_letter_source", "dead_letter_events", ["source_type", "source_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_dead_letter_source", table_name="dead_letter_events")
    op.drop_index("ix_dead_letter_org_status_created", table_name="dead_letter_events")
    op.drop_table("dead_letter_events")
