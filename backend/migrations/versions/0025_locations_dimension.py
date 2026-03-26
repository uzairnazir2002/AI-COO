"""locations dimension for transactions, analytics, and reports

Revision ID: 0025_locations_dimension
Revises: 0024_org_budget_threshold_setting
Create Date: 2026-03-27 00:15:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0025_locations_dimension"
down_revision: str | None = "0024_org_budget_threshold_setting"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_location_org_name"),
    )
    op.create_index("ix_location_org_active", "locations", ["org_id", "is_active"], unique=False)
    op.alter_column("locations", "is_active", server_default=None)

    op.add_column("transactions", sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_transactions_location_id", "transactions", "locations", ["location_id"], ["id"])
    op.create_index("ix_tx_org_location_date", "transactions", ["org_id", "location_id", "date"], unique=False)

    op.add_column("reports", sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_reports_location_id", "reports", "locations", ["location_id"], ["id"])
    op.drop_constraint("uq_report_org_week", "reports", type_="unique")
    op.create_index(
        "uq_report_org_week_global",
        "reports",
        ["org_id", "week_start"],
        unique=True,
        postgresql_where=sa.text("location_id IS NULL"),
    )
    op.create_index(
        "uq_report_org_week_location",
        "reports",
        ["org_id", "week_start", "location_id"],
        unique=True,
        postgresql_where=sa.text("location_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_report_org_week_location", table_name="reports")
    op.drop_index("uq_report_org_week_global", table_name="reports")
    op.create_unique_constraint("uq_report_org_week", "reports", ["org_id", "week_start"])
    op.drop_constraint("fk_reports_location_id", "reports", type_="foreignkey")
    op.drop_column("reports", "location_id")

    op.drop_index("ix_tx_org_location_date", table_name="transactions")
    op.drop_constraint("fk_transactions_location_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "location_id")

    op.drop_index("ix_location_org_active", table_name="locations")
    op.drop_table("locations")
