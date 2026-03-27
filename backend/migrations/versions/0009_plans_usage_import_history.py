"""add plans usage meters and transaction imports

Revision ID: 0009_plans_usage_import_history
Revises: 0008_alerts_open_partial_index
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_plans_usage_import_history"
down_revision = "0008_alerts_open_partial_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False, server_default="FREE"),
        sa.Column("transaction_limit_monthly", sa.Integer(), nullable=False, server_default="10000"),
        sa.Column("report_limit_monthly", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("ai_summary_limit_monthly", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )
    op.alter_column("organization_plans", "code", server_default=None)
    op.alter_column("organization_plans", "transaction_limit_monthly", server_default=None)
    op.alter_column("organization_plans", "report_limit_monthly", server_default=None)
    op.alter_column("organization_plans", "ai_summary_limit_monthly", server_default=None)

    op.create_table(
        "usage_meters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("soft_limit", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "metric", "period_start", name="uq_usage_org_metric_period"),
    )
    op.create_index("ix_usage_org_period", "usage_meters", ["org_id", "period_start"])
    op.alter_column("usage_meters", "used_count", server_default=None)

    op.create_table(
        "transaction_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mapping_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_rows_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tx_import_org_created", "transaction_imports", ["org_id", "created_at"])
    op.create_index("ix_tx_import_org_status", "transaction_imports", ["org_id", "status"])
    op.alter_column("transaction_imports", "total_rows", server_default=None)
    op.alter_column("transaction_imports", "inserted_count", server_default=None)
    op.alter_column("transaction_imports", "duplicate_count", server_default=None)
    op.alter_column("transaction_imports", "error_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tx_import_org_status", table_name="transaction_imports")
    op.drop_index("ix_tx_import_org_created", table_name="transaction_imports")
    op.drop_table("transaction_imports")
    op.drop_index("ix_usage_org_period", table_name="usage_meters")
    op.drop_table("usage_meters")
    op.drop_table("organization_plans")
