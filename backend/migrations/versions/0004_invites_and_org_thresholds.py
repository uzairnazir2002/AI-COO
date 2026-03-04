"""add invite tokens and org thresholds

Revision ID: 0004_invites_and_org_thresholds
Revises: 0003_job_states
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_invites_and_org_thresholds"
down_revision = "0003_job_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column("runway_alert_threshold_days", sa.Integer(), nullable=False, server_default="60"),
    )
    op.add_column(
        "organization_settings",
        sa.Column(
            "vendor_concentration_threshold_pct",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="50.00",
        ),
    )
    op.add_column(
        "organization_settings",
        sa.Column("misc_growth_multiplier", sa.Numeric(5, 2), nullable=False, server_default="1.40"),
    )
    op.add_column(
        "organization_settings",
        sa.Column("anomaly_spike_multiplier", sa.Numeric(5, 2), nullable=False, server_default="1.50"),
    )
    op.create_table(
        "organization_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_invites_org_email_status",
        "organization_invites",
        ["org_id", "email", "accepted_at"],
    )
    op.create_index("ix_invites_token_hash", "organization_invites", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_invites_token_hash", table_name="organization_invites")
    op.drop_index("ix_invites_org_email_status", table_name="organization_invites")
    op.drop_table("organization_invites")
    op.drop_column("organization_settings", "anomaly_spike_multiplier")
    op.drop_column("organization_settings", "misc_growth_multiplier")
    op.drop_column("organization_settings", "vendor_concentration_threshold_pct")
    op.drop_column("organization_settings", "runway_alert_threshold_days")
