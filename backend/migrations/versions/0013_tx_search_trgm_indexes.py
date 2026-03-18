"""add trigram indexes for transaction ilike search

Revision ID: 0013_tx_search_trgm
Revises: 0012_import_profiles
Create Date: 2026-03-13
"""

from alembic import op


revision = "0013_tx_search_trgm"
down_revision = "0012_import_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tx_vendor_trgm "
        "ON transactions USING gin (vendor gin_trgm_ops) "
        "WHERE vendor IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tx_notes_trgm "
        "ON transactions USING gin (notes gin_trgm_ops) "
        "WHERE notes IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tx_category_trgm "
        "ON transactions USING gin (category gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tx_category_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tx_notes_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tx_vendor_trgm")
