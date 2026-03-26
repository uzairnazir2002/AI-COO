"""privacy and deletion baseline

Revision ID: 0019_privacy_and_deletion_baseline
Revises: 0018_owner_security_policy
Create Date: 2026-03-25 01:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0019_privacy_and_deletion_baseline"
down_revision: str | None = "0018_owner_security_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"], unique=False)
    op.create_index(op.f("ix_organizations_deleted_at"), "organizations", ["deleted_at"], unique=False)

    op.alter_column("organization_billing", "billing_email", existing_type=sa.VARCHAR(length=255), type_=sa.String(length=1024))
    op.alter_column("organization_invites", "email", existing_type=sa.VARCHAR(length=255), type_=sa.String(length=1024))
    op.alter_column("token_sessions", "user_agent", existing_type=sa.VARCHAR(length=255), type_=sa.String(length=1024))
    op.alter_column("token_sessions", "ip_address", existing_type=sa.VARCHAR(length=100), type_=sa.String(length=255))

    op.create_table(
        "deletion_requests",
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("delete_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_org_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deletion_requests_due", "deletion_requests", ["status", "delete_after"], unique=False)
    op.create_index(
        "ix_deletion_requests_scope",
        "deletion_requests",
        ["scope", "target_user_id", "target_org_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_deletion_requests_scope", table_name="deletion_requests")
    op.drop_index("ix_deletion_requests_due", table_name="deletion_requests")
    op.drop_table("deletion_requests")

    op.alter_column("token_sessions", "ip_address", existing_type=sa.String(length=255), type_=sa.VARCHAR(length=100))
    op.alter_column("token_sessions", "user_agent", existing_type=sa.String(length=1024), type_=sa.VARCHAR(length=255))
    op.alter_column("organization_invites", "email", existing_type=sa.String(length=1024), type_=sa.VARCHAR(length=255))
    op.alter_column("organization_billing", "billing_email", existing_type=sa.String(length=1024), type_=sa.VARCHAR(length=255))

    op.drop_index(op.f("ix_organizations_deleted_at"), table_name="organizations")
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_column("organizations", "deleted_at")
    op.drop_column("users", "deleted_at")
