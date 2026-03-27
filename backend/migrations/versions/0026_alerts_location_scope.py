"""add location scope to persisted alerts

Revision ID: 0026_alerts_location_scope
Revises: 0025_locations_dimension
Create Date: 2026-03-27 03:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0026_alerts_location_scope"
down_revision: str | None = "0025_locations_dimension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("alerts", sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_alerts_location_id",
        "alerts",
        "locations",
        ["location_id"],
        ["id"],
    )
    op.create_index(
        "ix_alert_org_location_status_created",
        "alerts",
        ["org_id", "location_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alert_org_location_status_created", table_name="alerts")
    op.drop_constraint("fk_alerts_location_id", "alerts", type_="foreignkey")
    op.drop_column("alerts", "location_id")
