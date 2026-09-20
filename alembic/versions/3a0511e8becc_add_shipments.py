"""add shipments

Revision ID: 3a0511e8becc
Revises: 6a8d6a06fe91
Create Date: 2026-09-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3a0511e8becc"
down_revision: str | None = "6a8d6a06fe91"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_order_id", sa.Integer(), nullable=False),
        sa.Column("carrier", sa.String(255), nullable=True),
        sa.Column("tracking_number", sa.String(255), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_order_id"], ["customer_orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_shipments_customer_order_id", "shipments", ["customer_order_id"])
    op.create_index("ix_shipments_created_by_id", "shipments", ["created_by_id"])

    op.create_table(
        "shipment_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("customer_order_line_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.UniqueConstraint("shipment_id", "customer_order_line_id", name="uq_shipment_lines_shipment_order_line"),
        sa.CheckConstraint("quantity > 0", name="ck_shipment_lines_quantity_positive"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_order_line_id"], ["customer_order_lines.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_shipment_lines_shipment_id", "shipment_lines", ["shipment_id"])
    op.create_index("ix_shipment_lines_customer_order_line_id", "shipment_lines", ["customer_order_line_id"])


def downgrade() -> None:
    op.drop_table("shipment_lines")
    op.drop_table("shipments")
