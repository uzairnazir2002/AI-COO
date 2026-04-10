"""workforce phase 1 foundation

Revision ID: 0029_workforce_phase1_foundation
Revises: 0028_ai_chat_assistant_foundation
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0029_workforce_phase1_foundation"
down_revision: str | None = "0028_ai_chat_assistant_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_departments",
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
        sa.UniqueConstraint("org_id", "name", name="uq_workforce_department_org_name"),
        sa.UniqueConstraint("org_id", "code", name="uq_workforce_department_org_code"),
    )
    op.create_index(
        "ix_workforce_department_org_active",
        "workforce_departments",
        ["org_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "workforce_titles",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("level", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_workforce_title_org_name"),
    )
    op.create_index(
        "ix_workforce_title_org_active",
        "workforce_titles",
        ["org_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "workforce_employees",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_code", sa.String(length=40), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employment_type", sa.String(length=16), nullable=False, server_default="FULL_TIME"),
        sa.Column("employment_status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("salary_type", sa.String(length=16), nullable=False, server_default="SALARIED"),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(14, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["workforce_departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manager_employee_id"], ["workforce_employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["title_id"], ["workforce_titles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "employee_code", name="uq_workforce_employee_org_code"),
    )
    op.create_index(
        "ix_workforce_employee_org_active",
        "workforce_employees",
        ["org_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_employee_org_department",
        "workforce_employees",
        ["org_id", "department_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_employee_org_title",
        "workforce_employees",
        ["org_id", "title_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_employee_org_manager",
        "workforce_employees",
        ["org_id", "manager_employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_employee_org_location",
        "workforce_employees",
        ["org_id", "location_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_employee_org_location", table_name="workforce_employees")
    op.drop_index("ix_workforce_employee_org_manager", table_name="workforce_employees")
    op.drop_index("ix_workforce_employee_org_title", table_name="workforce_employees")
    op.drop_index("ix_workforce_employee_org_department", table_name="workforce_employees")
    op.drop_index("ix_workforce_employee_org_active", table_name="workforce_employees")
    op.drop_table("workforce_employees")

    op.drop_index("ix_workforce_title_org_active", table_name="workforce_titles")
    op.drop_table("workforce_titles")

    op.drop_index("ix_workforce_department_org_active", table_name="workforce_departments")
    op.drop_table("workforce_departments")

