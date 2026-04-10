"""workforce payroll unpaid leave deduction snapshot

Revision ID: 0033_workforce_payroll_unpaid_leave_deduction
Revises: 0032_workforce_payroll
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_workforce_payroll_unpaid_leave_deduction"
down_revision: str | None = "0032_workforce_payroll"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workforce_payroll_entries",
        sa.Column("unpaid_leave_deduction", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.alter_column("workforce_payroll_entries", "unpaid_leave_deduction", server_default=None)


def downgrade() -> None:
    op.drop_column("workforce_payroll_entries", "unpaid_leave_deduction")
