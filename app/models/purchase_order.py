from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.models.warehouse import Warehouse


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class PurchaseOrder(Base, TimestampMixin):
    """An order placed with a supplier to restock a warehouse. draft -> submitted -> (partially)
    received, or cancelled while nothing has been received yet."""

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(
            PurchaseOrderStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    supplier: Mapped[Supplier] = relationship()
    warehouse: Mapped[Warehouse] = relationship()
    created_by: Mapped[User] = relationship()
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan"
    )


class PurchaseOrderLine(Base):
    """One product/quantity/price line on a PurchaseOrder. Lines have no existence independent of
    their order (CASCADE), unlike the order itself, which is never hard-deleted."""

    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "product_id", name="uq_po_lines_order_product"),
        CheckConstraint("quantity_ordered > 0", name="ck_po_lines_quantity_ordered_positive"),
        CheckConstraint("quantity_received >= 0", name="ck_po_lines_quantity_received_non_negative"),
        CheckConstraint("quantity_received <= quantity_ordered", name="ck_po_lines_no_over_receipt"),
        CheckConstraint("unit_price >= 0", name="ck_po_lines_unit_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity_ordered: Mapped[int] = mapped_column(nullable=False)
    quantity_received: Mapped[int] = mapped_column(default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()
