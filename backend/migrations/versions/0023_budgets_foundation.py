"""budgets foundation

Revision ID: 0023_budgets_foundation
Revises: 0022_payment_integrations_stripe_foundation
Create Date: 2026-03-26 19:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0023_budgets_foundation"
down_revision: str | None = "0022_payment_integrations_stripe_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("budget_type", sa.String(length=16), nullable=False),
        sa.Column("planned_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "category",
            "period_month",
            "budget_type",
            "version",
            name="uq_budget_org_category_period_type_version",
        ),
    )
    op.create_index("ix_budget_org_period_current", "budgets", ["org_id", "period_month", "is_current"], unique=False)
    op.create_index("ix_budget_org_type_period", "budgets", ["org_id", "budget_type", "period_month"], unique=False)
    op.create_index("ix_budget_org_category_period", "budgets", ["org_id", "category", "period_month"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_budget_org_category_period", table_name="budgets")
    op.drop_index("ix_budget_org_type_period", table_name="budgets")
    op.drop_index("ix_budget_org_period_current", table_name="budgets")
    op.drop_table("budgets")
