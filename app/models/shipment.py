from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.customer_order import CustomerOrder, CustomerOrderLine
from app.models.product import Product
from app.models.user import User


class ShipmentStatus(StrEnum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Shipment(Base, TimestampMixin):
    """A physical shipment fulfilling some or all of a CustomerOrder's remaining lines. Creating
    one immediately moves the physical/reserved stock (see shipment_service.create_shipment)."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_order_id: Mapped[int] = mapped_column(
        ForeignKey("customer_orders.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    carrier: Mapped[str | None] = mapped_column(String(255))
    tracking_number: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ShipmentStatus] = mapped_column(
        Enum(
            ShipmentStatus,
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ShipmentStatus.PENDING,
        nullable=False,
    )
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    customer_order: Mapped[CustomerOrder] = relationship()
    created_by: Mapped[User] = relationship()
    lines: Mapped[list["ShipmentLine"]] = relationship(back_populates="shipment", cascade="all, delete-orphan")


class ShipmentLine(Base):
    """One product/quantity line on a Shipment, tied to the CustomerOrderLine it fulfills. Stays
    normalized through customer_order_line rather than denormalizing product_id/warehouse_id."""

    __tablename__ = "shipment_lines"
    __table_args__ = (
        UniqueConstraint("shipment_id", "customer_order_line_id", name="uq_shipment_lines_shipment_order_line"),
        CheckConstraint("quantity > 0", name="ck_shipment_lines_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer_order_line_id: Mapped[int] = mapped_column(
        ForeignKey("customer_order_lines.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="lines")
    customer_order_line: Mapped[CustomerOrderLine] = relationship()

    @property
    def product(self) -> Product:
        return self.customer_order_line.product
