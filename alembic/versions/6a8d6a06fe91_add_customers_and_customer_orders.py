"""add customers and customer orders

Revision ID: 6a8d6a06fe91
Revises: 7129c6eb1e88
Create Date: 2026-09-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "6a8d6a06fe91"
down_revision: str | None = "7129c6eb1e88"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # stock reservation - held for confirmed-but-not-yet-shipped customer order lines
    op.add_column("stock", sa.Column("reserved_quantity", sa.Integer(), server_default="0", nullable=False))
    op.create_check_constraint("ck_stock_reserved_quantity_non_negative", "stock", "reserved_quantity >= 0")
    op.create_check_constraint(
        "ck_stock_reserved_quantity_not_over_physical", "stock", "reserved_quantity <= quantity"
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_customers_name", "customers", ["name"])

    op.create_table(
        "customer_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(17), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_customer_orders_customer_id", "customer_orders", ["customer_id"])
    op.create_index("ix_customer_orders_warehouse_id", "customer_orders", ["warehouse_id"])
    op.create_index("ix_customer_orders_created_by_id", "customer_orders", ["created_by_id"])

    op.create_table(
        "customer_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_shipped", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint("customer_order_id", "product_id", name="uq_co_lines_order_product"),
        sa.CheckConstraint("quantity_ordered > 0", name="ck_co_lines_quantity_ordered_positive"),
        sa.CheckConstraint("quantity_shipped >= 0", name="ck_co_lines_quantity_shipped_non_negative"),
        sa.CheckConstraint("quantity_shipped <= quantity_ordered", name="ck_co_lines_no_over_shipment"),
        sa.CheckConstraint("unit_price >= 0", name="ck_co_lines_unit_price_non_negative"),
        sa.ForeignKeyConstraint(["customer_order_id"], ["customer_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_customer_order_lines_customer_order_id", "customer_order_lines", ["customer_order_id"])
    op.create_index("ix_customer_order_lines_product_id", "customer_order_lines", ["product_id"])


def downgrade() -> None:
    op.drop_table("customer_order_lines")
    op.drop_table("customer_orders")
    op.drop_table("customers")
    op.drop_constraint("ck_stock_reserved_quantity_not_over_physical", "stock", type_="check")
    op.drop_constraint("ck_stock_reserved_quantity_non_negative", "stock", type_="check")
    op.drop_column("stock", "reserved_quantity")
