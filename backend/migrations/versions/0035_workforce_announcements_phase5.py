"""workforce announcements: templates, deliveries, audience, email flag, attachments

Revision ID: 0035_workforce_announcements_phase5
Revises: 0034_workforce_announcements
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035_workforce_announcements_phase5"
down_revision: str | None = "0034_workforce_announcements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workforce_announcement_templates",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("automation_key", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workforce_ann_tpl_org", "workforce_announcement_templates", ["org_id"], unique=False)
    op.create_index(
        "uq_workforce_ann_tpl_org_code",
        "workforce_announcement_templates",
        ["org_id", "code"],
        unique=True,
        postgresql_where=sa.text("code IS NOT NULL AND btrim(code) <> ''"),
    )

    op.add_column(
        "workforce_announcements",
        sa.Column("audience_kind", sa.String(length=24), nullable=False, server_default="ORG_ALL"),
    )
    op.add_column("workforce_announcements", sa.Column("audience_ids", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "workforce_announcements",
        sa.Column("attachments_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "workforce_announcements",
        sa.Column("send_email_on_publish", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("workforce_announcements", sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_workforce_announcements_template_id",
        "workforce_announcements",
        "workforce_announcement_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_workforce_announcement_org_audience", "workforce_announcements", ["org_id", "audience_kind"])

    op.create_table(
        "workforce_announcement_deliveries",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False, server_default="email"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["announcement_id"], ["workforce_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outbox_event_id"], ["outbox_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workforce_ann_delivery_announcement", "workforce_announcement_deliveries", ["announcement_id"], unique=False
    )
    op.create_index("ix_workforce_ann_delivery_org", "workforce_announcement_deliveries", ["org_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workforce_ann_delivery_org", table_name="workforce_announcement_deliveries")
    op.drop_index("ix_workforce_ann_delivery_announcement", table_name="workforce_announcement_deliveries")
    op.drop_table("workforce_announcement_deliveries")

    op.drop_index("ix_workforce_announcement_org_audience", table_name="workforce_announcements")
    op.drop_constraint("fk_workforce_announcements_template_id", "workforce_announcements", type_="foreignkey")
    op.drop_column("workforce_announcements", "template_id")
    op.drop_column("workforce_announcements", "send_email_on_publish")
    op.drop_column("workforce_announcements", "attachments_json")
    op.drop_column("workforce_announcements", "audience_ids")
    op.drop_column("workforce_announcements", "audience_kind")

    op.drop_index("uq_workforce_ann_tpl_org_code", table_name="workforce_announcement_templates")
    op.drop_index("ix_workforce_ann_tpl_org", table_name="workforce_announcement_templates")
    op.drop_table("workforce_announcement_templates")
