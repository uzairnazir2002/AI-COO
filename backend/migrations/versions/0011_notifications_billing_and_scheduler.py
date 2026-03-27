"""add durable notifications, stripe billing fields, and scheduler controls

Revision ID: 0011_ops_billing
Revises: 0010_confirm_and_billing
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_ops_billing"
down_revision = "0010_confirm_and_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=255), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_org_created", "notifications", ["user_id", "org_id", "created_at"], unique=False)
    op.create_table(
        "schedule_controls",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.add_column("organization_billing", sa.Column("provider", sa.String(length=32), nullable=False, server_default="MANUAL"))
    op.add_column("organization_billing", sa.Column("customer_id", sa.String(length=128), nullable=True))
    op.add_column("organization_billing", sa.Column("subscription_id", sa.String(length=128), nullable=True))
    op.add_column("organization_billing", sa.Column("subscription_status", sa.String(length=64), nullable=True))
    op.add_column("organization_billing", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organization_billing", sa.Column("active_price_id", sa.String(length=128), nullable=True))
    op.alter_column("organization_billing", "provider", server_default=None)
    op.execute(
        """
        INSERT INTO schedule_controls (name, paused, updated_at)
        VALUES
          ('weekly-reports', false, NOW()),
          ('outbox-consumer', false, NOW())
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_column("organization_billing", "active_price_id")
    op.drop_column("organization_billing", "current_period_end")
    op.drop_column("organization_billing", "subscription_status")
    op.drop_column("organization_billing", "subscription_id")
    op.drop_column("organization_billing", "customer_id")
    op.drop_column("organization_billing", "provider")
    op.drop_table("schedule_controls")
    op.drop_index("ix_notifications_user_org_created", table_name="notifications")
    op.drop_table("notifications")
