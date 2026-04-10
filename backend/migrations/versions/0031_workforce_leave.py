"""workforce leave

Revision ID: 0031_workforce_leave
Revises: 0030_workforce_attendance_and_shifts
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0031_workforce_leave"
down_revision: str | None = "0030_workforce_attendance_and_shifts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_leave_types",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_workforce_leave_type_org_name"),
        sa.UniqueConstraint("org_id", "code", name="uq_workforce_leave_type_org_code"),
    )
    op.create_index(
        "ix_workforce_leave_type_org_active", "workforce_leave_types", ["org_id", "is_active"], unique=False
    )

    op.create_table(
        "workforce_leave_balances",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated_days", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("used_days", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("pending_days", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["workforce_leave_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "employee_id", "leave_type_id", "year", name="uq_workforce_leave_balance_org_emp_type_year"
        ),
    )
    op.create_index(
        "ix_workforce_leave_balance_org_employee", "workforce_leave_balances", ["org_id", "employee_id"], unique=False
    )
    op.create_index(
        "ix_workforce_leave_balance_org_type", "workforce_leave_balances", ["org_id", "leave_type_id"], unique=False
    )
    op.create_index(
        "ix_workforce_leave_balance_org_year", "workforce_leave_balances", ["org_id", "year"], unique=False
    )

    op.create_table(
        "workforce_leave_requests",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leave_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_note", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_type_id"], ["workforce_leave_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workforce_leave_req_org_status", "workforce_leave_requests", ["org_id", "status"], unique=False
    )
    op.create_index(
        "ix_workforce_leave_req_org_employee_start",
        "workforce_leave_requests",
        ["org_id", "employee_id", "start_date"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_leave_req_org_dates", "workforce_leave_requests", ["org_id", "start_date", "end_date"], unique=False
    )
    op.create_index(
        "ix_workforce_leave_req_org_type", "workforce_leave_requests", ["org_id", "leave_type_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_leave_req_org_type", table_name="workforce_leave_requests")
    op.drop_index("ix_workforce_leave_req_org_dates", table_name="workforce_leave_requests")
    op.drop_index("ix_workforce_leave_req_org_employee_start", table_name="workforce_leave_requests")
    op.drop_index("ix_workforce_leave_req_org_status", table_name="workforce_leave_requests")
    op.drop_table("workforce_leave_requests")

    op.drop_index("ix_workforce_leave_balance_org_year", table_name="workforce_leave_balances")
    op.drop_index("ix_workforce_leave_balance_org_type", table_name="workforce_leave_balances")
    op.drop_index("ix_workforce_leave_balance_org_employee", table_name="workforce_leave_balances")
    op.drop_table("workforce_leave_balances")

    op.drop_index("ix_workforce_leave_type_org_active", table_name="workforce_leave_types")
    op.drop_table("workforce_leave_types")

