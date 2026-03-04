"""add job states

Revision ID: 0003_job_states
Revises: 0002_categories
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_job_states"
down_revision = "0002_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_job_state_dedupe", "job_states", ["dedupe_key"])


def downgrade() -> None:
    op.drop_constraint("uq_job_state_dedupe", "job_states", type_="unique")
    op.drop_table("job_states")
