"""inventory forecasting foundation

Revision ID: 0027_inventory_forecasting_foundation
Revises: 0026_alerts_location_scope
Create Date: 2026-03-27 06:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0027_inventory_forecasting_foundation"
down_revision: str | None = "0026_alerts_location_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "sku", "location_id", name="uq_inventory_item_org_sku_location"),
    )
    op.create_index("ix_inventory_item_org_active", "inventory_items", ["org_id", "is_active"], unique=False)
    op.create_index("ix_inventory_item_org_location", "inventory_items", ["org_id", "location_id"], unique=False)

    op.create_table(
        "inventory_stock_levels",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("on_hand_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("reserved_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "item_id", "location_id", name="uq_inventory_stock_level_org_item_location"),
    )
    op.create_index("ix_inventory_stock_level_org_item", "inventory_stock_levels", ["org_id", "item_id"], unique=False)
    op.create_index(
        "ix_inventory_stock_level_org_location",
        "inventory_stock_levels",
        ["org_id", "location_id"],
        unique=False,
    )

    op.create_table(
        "inventory_stock_events",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("delta_qty", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_stock_event_org_item_occurred",
        "inventory_stock_events",
        ["org_id", "item_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_stock_event_org_location_occurred",
        "inventory_stock_events",
        ["org_id", "location_id", "occurred_at"],
        unique=False,
    )

    op.create_table(
        "inventory_purchase_orders",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("received_qty", sa.Numeric(14, 3), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="OPEN"),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_po_org_status_expected",
        "inventory_purchase_orders",
        ["org_id", "status", "expected_date"],
        unique=False,
    )
    op.create_index(
        "ix_inventory_po_org_item_status",
        "inventory_purchase_orders",
        ["org_id", "item_id", "status"],
        unique=False,
    )

    op.create_table(
        "inventory_sales_velocity",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("units_per_day", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("basis_start", sa.Date(), nullable=False),
        sa.Column("basis_end", sa.Date(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["inventory_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id",
            "item_id",
            "location_id",
            "window_days",
            name="uq_inventory_sales_velocity_org_item_location_window",
        ),
    )
    op.create_index(
        "ix_inventory_sales_velocity_org_item",
        "inventory_sales_velocity",
        ["org_id", "item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_sales_velocity_org_item", table_name="inventory_sales_velocity")
    op.drop_table("inventory_sales_velocity")
    op.drop_index("ix_inventory_po_org_item_status", table_name="inventory_purchase_orders")
    op.drop_index("ix_inventory_po_org_status_expected", table_name="inventory_purchase_orders")
    op.drop_table("inventory_purchase_orders")
    op.drop_index("ix_inventory_stock_event_org_location_occurred", table_name="inventory_stock_events")
    op.drop_index("ix_inventory_stock_event_org_item_occurred", table_name="inventory_stock_events")
    op.drop_table("inventory_stock_events")
    op.drop_index("ix_inventory_stock_level_org_location", table_name="inventory_stock_levels")
    op.drop_index("ix_inventory_stock_level_org_item", table_name="inventory_stock_levels")
    op.drop_table("inventory_stock_levels")
    op.drop_index("ix_inventory_item_org_location", table_name="inventory_items")
    op.drop_index("ix_inventory_item_org_active", table_name="inventory_items")
    op.drop_table("inventory_items")
