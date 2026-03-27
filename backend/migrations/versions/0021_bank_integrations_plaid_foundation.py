"""bank integrations plaid foundation

Revision ID: 0021_bank_integrations_plaid_foundation
Revises: 0020_dead_letter_events
Create Date: 2026-03-25 23:55:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0021_bank_integrations_plaid_foundation"
down_revision: str | None = "0020_dead_letter_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bank_connections",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("external_item_id", sa.String(length=255), nullable=False),
        sa.Column("institution_id", sa.String(length=255), nullable=True),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("access_token_ref", sa.String(length=1024), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "provider", "external_item_id", name="uq_bank_conn_org_provider_item"),
    )
    op.create_index("ix_bank_conn_org_status", "bank_connections", ["org_id", "status"], unique=False)

    op.create_table(
        "bank_accounts",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_account_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mask", sa.String(length=16), nullable=True),
        sa.Column("account_type", sa.String(length=64), nullable=True),
        sa.Column("account_subtype", sa.String(length=64), nullable=True),
        sa.Column("currency_code", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["bank_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "external_account_id", name="uq_bank_acct_conn_external"),
    )
    op.create_index("ix_bank_acct_org_conn", "bank_accounts", ["org_id", "connection_id"], unique=False)

    op.create_table(
        "bank_sync_cursors",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cursor", sa.String(length=1024), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["bank_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id"),
    )
    op.create_index("ix_bank_cursor_org_conn", "bank_sync_cursors", ["org_id", "connection_id"], unique=True)

    op.create_table(
        "bank_sync_runs",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_before", sa.String(length=1024), nullable=True),
        sa.Column("cursor_after", sa.String(length=1024), nullable=True),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["bank_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bank_sync_run_org_status_created",
        "bank_sync_runs",
        ["org_id", "status", "created_at"],
        unique=False,
    )
    op.create_index("ix_bank_sync_run_conn_created", "bank_sync_runs", ["connection_id", "created_at"], unique=False)

    op.create_table(
        "bank_synced_transactions",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_transaction_id", sa.String(length=255), nullable=False),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency_code", sa.String(length=16), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["bank_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("connection_id", "external_transaction_id", name="uq_bank_synced_conn_external_tx"),
    )
    op.create_index(
        "ix_bank_synced_org_external",
        "bank_synced_transactions",
        ["org_id", "external_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bank_synced_org_external", table_name="bank_synced_transactions")
    op.drop_table("bank_synced_transactions")
    op.drop_index("ix_bank_sync_run_conn_created", table_name="bank_sync_runs")
    op.drop_index("ix_bank_sync_run_org_status_created", table_name="bank_sync_runs")
    op.drop_table("bank_sync_runs")
    op.drop_index("ix_bank_cursor_org_conn", table_name="bank_sync_cursors")
    op.drop_table("bank_sync_cursors")
    op.drop_index("ix_bank_acct_org_conn", table_name="bank_accounts")
    op.drop_table("bank_accounts")
    op.drop_index("ix_bank_conn_org_status", table_name="bank_connections")
    op.drop_table("bank_connections")
