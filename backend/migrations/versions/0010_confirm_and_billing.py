"""add registration confirmation tokens and billing placeholders

Revision ID: 0010_confirm_and_billing
Revises: 0009_plans_usage_import_history
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_confirm_and_billing"
down_revision = "0009_plans_usage_import_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_confirmation_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_confirm_token_hash", "account_confirmation_tokens", ["token_hash"], unique=True)

    op.create_table(
        "organization_billing",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("billing_email", sa.String(length=255), nullable=True),
        sa.Column("invoice_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plan_label", sa.String(length=64), nullable=False, server_default="FREE"),
        sa.Column("billing_notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )
    op.alter_column("organization_billing", "invoice_enabled", server_default=None)
    op.alter_column("organization_billing", "plan_label", server_default=None)

def downgrade() -> None:
    op.drop_table("organization_billing")
    op.drop_index("ix_account_confirm_token_hash", table_name="account_confirmation_tokens")
    op.drop_table("account_confirmation_tokens")
