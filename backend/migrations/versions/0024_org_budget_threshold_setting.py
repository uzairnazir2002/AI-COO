"""org budget variance threshold setting

Revision ID: 0024_org_budget_threshold_setting
Revises: 0023_budgets_foundation
Create Date: 2026-03-26 22:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0024_org_budget_threshold_setting"
down_revision: str | None = "0023_budgets_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_settings",
        sa.Column(
            "budget_variance_alert_threshold_pct",
            sa.Numeric(precision=6, scale=2),
            nullable=False,
            server_default="10.00",
        ),
    )
    op.alter_column("organization_settings", "budget_variance_alert_threshold_pct", server_default=None)


def downgrade() -> None:
    op.drop_column("organization_settings", "budget_variance_alert_threshold_pct")

