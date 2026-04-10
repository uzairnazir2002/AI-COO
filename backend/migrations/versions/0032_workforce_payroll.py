"""workforce payroll

Revision ID: 0032_workforce_payroll
Revises: 0031_workforce_leave
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0032_workforce_payroll"
down_revision: str | None = "0031_workforce_leave"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_payroll_periods",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "start_date", "end_date", name="uq_workforce_payroll_period_org_range"),
    )
    op.create_index(
        "ix_workforce_payroll_period_org_start", "workforce_payroll_periods", ["org_id", "start_date"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_period_org_status", "workforce_payroll_periods", ["org_id", "status"], unique=False
    )

    op.create_table(
        "workforce_payroll_entries",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payroll_period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("salary_type", sa.String(length=16), nullable=False, server_default="SALARIED"),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(14, 2), nullable=True),
        sa.Column("overtime_multiplier", sa.Numeric(6, 2), nullable=False, server_default="1.5"),
        sa.Column("worked_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payable_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("gross_pay", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("adjustments_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["workforce_payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "payroll_period_id", "employee_id", name="uq_workforce_payroll_entry_org_period_emp"
        ),
    )
    op.create_index(
        "ix_workforce_payroll_entry_org_period", "workforce_payroll_entries", ["org_id", "payroll_period_id"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_entry_org_employee", "workforce_payroll_entries", ["org_id", "employee_id"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_entry_org_status", "workforce_payroll_entries", ["org_id", "status"], unique=False
    )

    op.create_table(
        "workforce_payroll_adjustments",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payroll_period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payroll_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_entry_id"], ["workforce_payroll_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payroll_period_id"], ["workforce_payroll_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workforce_payroll_adj_org_period", "workforce_payroll_adjustments", ["org_id", "payroll_period_id"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_adj_org_entry", "workforce_payroll_adjustments", ["org_id", "payroll_entry_id"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_adj_org_employee", "workforce_payroll_adjustments", ["org_id", "employee_id"], unique=False
    )
    op.create_index(
        "ix_workforce_payroll_adj_org_kind", "workforce_payroll_adjustments", ["org_id", "kind"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_payroll_adj_org_kind", table_name="workforce_payroll_adjustments")
    op.drop_index("ix_workforce_payroll_adj_org_employee", table_name="workforce_payroll_adjustments")
    op.drop_index("ix_workforce_payroll_adj_org_entry", table_name="workforce_payroll_adjustments")
    op.drop_index("ix_workforce_payroll_adj_org_period", table_name="workforce_payroll_adjustments")
    op.drop_table("workforce_payroll_adjustments")

    op.drop_index("ix_workforce_payroll_entry_org_status", table_name="workforce_payroll_entries")
    op.drop_index("ix_workforce_payroll_entry_org_employee", table_name="workforce_payroll_entries")
    op.drop_index("ix_workforce_payroll_entry_org_period", table_name="workforce_payroll_entries")
    op.drop_table("workforce_payroll_entries")

    op.drop_index("ix_workforce_payroll_period_org_status", table_name="workforce_payroll_periods")
    op.drop_index("ix_workforce_payroll_period_org_start", table_name="workforce_payroll_periods")
    op.drop_table("workforce_payroll_periods")

