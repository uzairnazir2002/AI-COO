"""workforce announcements and receipts

Revision ID: 0034_workforce_announcements
Revises: 0033_workforce_payroll_unpaid_leave_deduction
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_workforce_announcements"
down_revision: str | None = "0033_workforce_payroll_unpaid_leave_deduction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_announcements",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("acknowledgement_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workforce_announcement_org_status", "workforce_announcements", ["org_id", "status"], unique=False)
    op.create_index(
        "ix_workforce_announcement_org_published",
        "workforce_announcements",
        ["org_id", "published_at"],
        unique=False,
    )

    op.create_table(
        "workforce_announcement_receipts",
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["announcement_id"], ["workforce_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_workforce_announcement_receipt_user"),
    )
    op.create_index(
        "ix_workforce_announcement_receipt_user", "workforce_announcement_receipts", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_workforce_announcement_receipt_user", table_name="workforce_announcement_receipts")
    op.drop_table("workforce_announcement_receipts")
    op.drop_index("ix_workforce_announcement_org_published", table_name="workforce_announcements")
    op.drop_index("ix_workforce_announcement_org_status", table_name="workforce_announcements")
    op.drop_table("workforce_announcements")
