"""add purchase orders

Revision ID: 7129c6eb1e88
Revises: 438cfde4e719
Create Date: 2026-09-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7129c6eb1e88"
down_revision: str | None = "438cfde4e719"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(18), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_warehouse_id", "purchase_orders", ["warehouse_id"])
    op.create_index("ix_purchase_orders_created_by_id", "purchase_orders", ["created_by_id"])

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("purchase_order_id", "product_id", name="uq_po_lines_order_product"),
        sa.CheckConstraint("quantity_ordered > 0", name="ck_po_lines_quantity_ordered_positive"),
        sa.CheckConstraint("quantity_received >= 0", name="ck_po_lines_quantity_received_non_negative"),
        sa.CheckConstraint("quantity_received <= quantity_ordered", name="ck_po_lines_no_over_receipt"),
        sa.CheckConstraint("unit_price >= 0", name="ck_po_lines_unit_price_non_negative"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_purchase_order_lines_purchase_order_id", "purchase_order_lines", ["purchase_order_id"])
    op.create_index("ix_purchase_order_lines_product_id", "purchase_order_lines", ["product_id"])


def downgrade() -> None:
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
