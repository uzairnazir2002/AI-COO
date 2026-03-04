"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )
    op.create_index("ix_membership_org_user", "memberships", ["org_id", "user_id"])
    op.create_table(
        "organization_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("starting_cash", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("vendor", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tx_org_date", "transactions", ["org_id", "date"])
    op.create_index("ix_tx_org_type_date", "transactions", ["org_id", "type", "date"])
    op.create_index("ix_tx_org_category_date", "transactions", ["org_id", "category", "date"])
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_alert_org_status_created", "alerts", ["org_id", "status", "created_at"])
    op.create_table(
        "forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=16), nullable=False),
        sa.Column("revenue_pred", sa.Numeric(14, 2), nullable=False),
        sa.Column("expense_pred", sa.Numeric(14, 2), nullable=False),
        sa.Column("confidence_low", sa.Numeric(14, 2), nullable=False),
        sa.Column("confidence_high", sa.Numeric(14, 2), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("org_id", "month", "scenario", name="uq_forecast_org_month_scenario"),
    )
    op.create_index("ix_forecast_org_month", "forecasts", ["org_id", "month"])
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "week_start", name="uq_report_org_week"),
    )
    op.create_index("ix_report_org_week", "reports", ["org_id", "week_start"])
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "token_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_token_sessions_hash", "token_sessions", ["refresh_token_hash"])
    op.create_index("ix_token_user_active", "token_sessions", ["user_id", "is_revoked"])
    op.create_table(
        "monthly_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("year_month", sa.Date(), nullable=False),
        sa.Column("revenue_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("expense_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("net_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("org_id", "year_month", name="uq_agg_org_month"),
    )


def downgrade() -> None:
    op.drop_table("monthly_aggregates")
    op.drop_index("ix_token_user_active", table_name="token_sessions")
    op.drop_table("token_sessions")
    op.drop_table("audit_logs")
    op.drop_index("ix_report_org_week", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_forecast_org_month", table_name="forecasts")
    op.drop_table("forecasts")
    op.drop_index("ix_alert_org_status_created", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_tx_org_category_date", table_name="transactions")
    op.drop_index("ix_tx_org_type_date", table_name="transactions")
    op.drop_index("ix_tx_org_date", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("organization_settings")
    op.drop_index("ix_membership_org_user", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("organizations")
    op.drop_table("users")
