"""workforce attendance and shifts

Revision ID: 0030_workforce_attendance_and_shifts
Revises: 0029_workforce_phase1_foundation
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0030_workforce_attendance_and_shifts"
down_revision: str | None = "0029_workforce_phase1_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_shifts",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("grace_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_workforce_shift_org_name"),
    )
    op.create_index("ix_workforce_shift_org_active", "workforce_shifts", ["org_id", "is_active"], unique=False)

    op.create_table(
        "workforce_shift_assignments",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shift_id"], ["workforce_shifts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "employee_id",
            "shift_id",
            "effective_from",
            name="uq_workforce_shift_assignment_org_emp_shift_from",
        ),
    )
    op.create_index(
        "ix_workforce_shift_assignment_org_employee",
        "workforce_shift_assignments",
        ["org_id", "employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_shift_assignment_org_shift",
        "workforce_shift_assignments",
        ["org_id", "shift_id"],
        unique=False,
    )

    op.create_table(
        "workforce_attendance_records",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PRESENT"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="CLOCK"),
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shift_assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("clock_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("minutes_late", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_checkout", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("worked_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payable_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shift_assignment_id"], ["workforce_shift_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shift_id"], ["workforce_shifts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "employee_id", "work_date", name="uq_workforce_attendance_org_emp_date"),
    )
    op.create_index(
        "ix_workforce_attendance_org_date",
        "workforce_attendance_records",
        ["org_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_attendance_org_employee_date",
        "workforce_attendance_records",
        ["org_id", "employee_id", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_attendance_org_status_date",
        "workforce_attendance_records",
        ["org_id", "status", "work_date"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_attendance_org_flags",
        "workforce_attendance_records",
        ["org_id", "is_late", "missing_checkout"],
        unique=False,
    )

    op.create_table(
        "workforce_attendance_corrections",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("proposed_clock_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_status", sa.String(length=16), nullable=True),
        sa.Column("reviewer_note", sa.String(length=500), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attendance_record_id"], ["workforce_attendance_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workforce_att_corr_org_status",
        "workforce_attendance_corrections",
        ["org_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_att_corr_org_employee",
        "workforce_attendance_corrections",
        ["org_id", "employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_att_corr_org_record",
        "workforce_attendance_corrections",
        ["org_id", "attendance_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_att_corr_org_record", table_name="workforce_attendance_corrections")
    op.drop_index("ix_workforce_att_corr_org_employee", table_name="workforce_attendance_corrections")
    op.drop_index("ix_workforce_att_corr_org_status", table_name="workforce_attendance_corrections")
    op.drop_table("workforce_attendance_corrections")

    op.drop_index("ix_workforce_attendance_org_flags", table_name="workforce_attendance_records")
    op.drop_index("ix_workforce_attendance_org_status_date", table_name="workforce_attendance_records")
    op.drop_index("ix_workforce_attendance_org_employee_date", table_name="workforce_attendance_records")
    op.drop_index("ix_workforce_attendance_org_date", table_name="workforce_attendance_records")
    op.drop_table("workforce_attendance_records")

    op.drop_index("ix_workforce_shift_assignment_org_shift", table_name="workforce_shift_assignments")
    op.drop_index("ix_workforce_shift_assignment_org_employee", table_name="workforce_shift_assignments")
    op.drop_table("workforce_shift_assignments")

    op.drop_index("ix_workforce_shift_org_active", table_name="workforce_shifts")
    op.drop_table("workforce_shifts")

