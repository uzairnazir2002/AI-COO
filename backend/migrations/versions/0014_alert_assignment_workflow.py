"""add alert assignment and acknowledgment fields

Revision ID: 0014_alert_assignment
Revises: 0013_tx_search_trgm
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_alert_assignment"
down_revision = "0013_tx_search_trgm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("alerts", sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_alert_org_status_assigned",
        "alerts",
        ["org_id", "status", "assigned_to_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alert_org_status_assigned", table_name="alerts")
    op.drop_column("alerts", "acknowledged_at")
    op.drop_column("alerts", "assigned_at")
    op.drop_column("alerts", "assigned_by_user_id")
    op.drop_column("alerts", "assigned_to_user_id")
