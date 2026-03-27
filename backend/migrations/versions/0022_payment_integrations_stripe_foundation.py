"""payment integrations stripe foundation

Revision ID: 0022_payment_integrations_stripe_foundation
Revises: 0021_bank_integrations_plaid_foundation
Create Date: 2026-03-26 00:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0022_payment_integrations_stripe_foundation"
down_revision: str | None = "0021_bank_integrations_plaid_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_processor_connections",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "provider", name="uq_payment_conn_org_provider"),
    )
    op.create_index(
        "ix_payment_conn_org_provider_status",
        "payment_processor_connections",
        ["org_id", "provider", "status"],
        unique=False,
    )

    op.create_table(
        "payment_webhook_events",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["payment_processor_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_webhook_provider_event"),
    )
    op.create_index(
        "ix_payment_webhook_org_status_created",
        "payment_webhook_events",
        ["org_id", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "payment_ledger_entries",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("webhook_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=False),
        sa.Column("entry_type", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency_code", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["payment_processor_connections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["webhook_event_id"], ["payment_webhook_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "provider", "external_event_id", "entry_type", name="uq_payment_ledger_event_type"),
    )
    op.create_index(
        "ix_payment_ledger_org_occurred",
        "payment_ledger_entries",
        ["org_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_payment_ledger_org_type_occurred",
        "payment_ledger_entries",
        ["org_id", "entry_type", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_ledger_org_type_occurred", table_name="payment_ledger_entries")
    op.drop_index("ix_payment_ledger_org_occurred", table_name="payment_ledger_entries")
    op.drop_table("payment_ledger_entries")
    op.drop_index("ix_payment_webhook_org_status_created", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_payment_conn_org_provider_status", table_name="payment_processor_connections")
    op.drop_table("payment_processor_connections")
