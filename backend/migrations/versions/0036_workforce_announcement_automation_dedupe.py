"""workforce announcements: automation dedupe key for template-triggered posts

Revision ID: 0036_workforce_announcement_automation_dedupe
Revises: 0035_workforce_announcements_phase5
Create Date: 2026-04-10 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_workforce_announcement_automation_dedupe"
down_revision: str | None = "0035_workforce_announcements_phase5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workforce_announcements",
        sa.Column("automation_dedupe_key", sa.String(length=128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_workforce_ann_org_automation_dedupe",
        "workforce_announcements",
        ["org_id", "automation_dedupe_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_workforce_ann_org_automation_dedupe", "workforce_announcements", type_="unique")
    op.drop_column("workforce_announcements", "automation_dedupe_key")
