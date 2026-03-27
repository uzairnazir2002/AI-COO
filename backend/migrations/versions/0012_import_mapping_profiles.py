"""add import mapping profiles and attach profile reference to imports

Revision ID: 0012_import_profiles
Revises: 0011_ops_billing
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_import_profiles"
down_revision = "0011_ops_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_mapping_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("column_map", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_profile_org_name", "import_mapping_profiles", ["org_id", "name"], unique=False)
    op.create_index("ix_import_profile_org_user", "import_mapping_profiles", ["org_id", "user_id"], unique=False)

    op.add_column(
        "transaction_imports",
        sa.Column("mapping_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_mapping_profiles.id"), nullable=True),
    )
    op.create_index("ix_tx_import_profile", "transaction_imports", ["mapping_profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tx_import_profile", table_name="transaction_imports")
    op.drop_column("transaction_imports", "mapping_profile_id")
    op.drop_index("ix_import_profile_org_user", table_name="import_mapping_profiles")
    op.drop_index("ix_import_profile_org_name", table_name="import_mapping_profiles")
    op.drop_table("import_mapping_profiles")
