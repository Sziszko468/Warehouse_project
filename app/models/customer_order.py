from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.customer import Customer
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse


class CustomerOrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class CustomerOrder(Base, TimestampMixin):
    """An order placed by a customer, fulfilled from a single warehouse. draft -> confirmed
    (reserves stock) -> (partially) shipped via one or more Shipments, or cancelled while nothing
    has shipped yet (releasing any reservation)."""

    __tablename__ = "customer_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    status: Mapped[CustomerOrderStatus] = mapped_column(
        Enum(
            CustomerOrderStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=CustomerOrderStatus.DRAFT,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship()
    warehouse: Mapped[Warehouse] = relationship()
    created_by: Mapped[User] = relationship()
    lines: Mapped[list["CustomerOrderLine"]] = relationship(
        back_populates="customer_order", cascade="all, delete-orphan"
    )


class CustomerOrderLine(Base):
    """One product/quantity line on a CustomerOrder. `unit_price` is snapshotted from
    Product.unit_price at order-creation time, not caller-supplied."""

    __tablename__ = "customer_order_lines"
    __table_args__ = (
        UniqueConstraint("customer_order_id", "product_id", name="uq_co_lines_order_product"),
        CheckConstraint("quantity_ordered > 0", name="ck_co_lines_quantity_ordered_positive"),
        CheckConstraint("quantity_shipped >= 0", name="ck_co_lines_quantity_shipped_non_negative"),
        CheckConstraint("quantity_shipped <= quantity_ordered", name="ck_co_lines_no_over_shipment"),
        CheckConstraint("unit_price >= 0", name="ck_co_lines_unit_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_order_id: Mapped[int] = mapped_column(
        ForeignKey("customer_orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity_ordered: Mapped[int] = mapped_column(nullable=False)
    quantity_shipped: Mapped[int] = mapped_column(default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    customer_order: Mapped[CustomerOrder] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()
