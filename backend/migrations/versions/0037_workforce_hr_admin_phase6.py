"""workforce hr admin phase 6

Revision ID: 0037_workforce_hr_admin_phase6
Revises: 0036_workforce_announcement_automation_dedupe
Create Date: 2026-04-23 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037_workforce_hr_admin_phase6"
down_revision: str | None = "0036_workforce_announcement_automation_dedupe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("workforce_employees", sa.Column("contract_start", sa.Date(), nullable=True))
    op.add_column("workforce_employees", sa.Column("contract_end", sa.Date(), nullable=True))
    op.add_column("workforce_employees", sa.Column("probation_end", sa.Date(), nullable=True))

    op.create_table(
        "workforce_policies",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("requires_ack", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "code", name="uq_workforce_policy_org_code"),
    )
    op.create_index("ix_workforce_policy_org_active", "workforce_policies", ["org_id", "is_active"], unique=False)
    op.create_index("ix_workforce_policy_org_published", "workforce_policies", ["org_id", "published_at"], unique=False)

    op.create_table(
        "workforce_policy_acknowledgements",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["workforce_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "policy_id", "employee_id", name="uq_workforce_policy_ack_org_policy_emp"),
    )
    op.create_index(
        "ix_workforce_policy_ack_org_policy",
        "workforce_policy_acknowledgements",
        ["org_id", "policy_id"],
        unique=False,
    )
    op.create_index(
        "ix_workforce_policy_ack_org_employee",
        "workforce_policy_acknowledgements",
        ["org_id", "employee_id"],
        unique=False,
    )

    op.create_table(
        "workforce_documents",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["workforce_policies.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workforce_document_org_employee", "workforce_documents", ["org_id", "employee_id"], unique=False)
    op.create_index("ix_workforce_document_org_policy", "workforce_documents", ["org_id", "policy_id"], unique=False)
    op.create_index("ix_workforce_document_org_active", "workforce_documents", ["org_id", "is_active"], unique=False)

    op.create_table(
        "workforce_checklist_items",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("details", sa.String(length=1000), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["workforce_employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workforce_checklist_org_employee", "workforce_checklist_items", ["org_id", "employee_id"], unique=False)
    op.create_index("ix_workforce_checklist_org_kind", "workforce_checklist_items", ["org_id", "kind"], unique=False)
    op.create_index(
        "ix_workforce_checklist_org_kind_done",
        "workforce_checklist_items",
        ["org_id", "kind", "is_done"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_checklist_org_kind_done", table_name="workforce_checklist_items")
    op.drop_index("ix_workforce_checklist_org_kind", table_name="workforce_checklist_items")
    op.drop_index("ix_workforce_checklist_org_employee", table_name="workforce_checklist_items")
    op.drop_table("workforce_checklist_items")

    op.drop_index("ix_workforce_document_org_active", table_name="workforce_documents")
    op.drop_index("ix_workforce_document_org_policy", table_name="workforce_documents")
    op.drop_index("ix_workforce_document_org_employee", table_name="workforce_documents")
    op.drop_table("workforce_documents")

    op.drop_index("ix_workforce_policy_ack_org_employee", table_name="workforce_policy_acknowledgements")
    op.drop_index("ix_workforce_policy_ack_org_policy", table_name="workforce_policy_acknowledgements")
    op.drop_table("workforce_policy_acknowledgements")

    op.drop_index("ix_workforce_policy_org_published", table_name="workforce_policies")
    op.drop_index("ix_workforce_policy_org_active", table_name="workforce_policies")
    op.drop_table("workforce_policies")

    op.drop_column("workforce_employees", "probation_end")
    op.drop_column("workforce_employees", "contract_end")
    op.drop_column("workforce_employees", "contract_start")

