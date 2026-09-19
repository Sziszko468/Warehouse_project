import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse


class MovementType(str, enum.Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"


class StockMovement(Base):
    """Immutable audit ledger for stock in/out/transfer operations. Never updated or deleted."""

    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_movements_quantity_positive"),
        CheckConstraint(
            "(movement_type = 'in' AND from_warehouse_id IS NULL AND to_warehouse_id IS NOT NULL) OR "
            "(movement_type = 'out' AND from_warehouse_id IS NOT NULL AND to_warehouse_id IS NULL) OR "
            "(movement_type = 'transfer' AND from_warehouse_id IS NOT NULL AND to_warehouse_id IS NOT NULL)",
            name="ck_stock_movements_warehouse_combination",
        ),
        # IS DISTINCT FROM (not !=) so this still evaluates correctly when one side is NULL (IN/OUT rows)
        CheckConstraint(
            "from_warehouse_id IS DISTINCT FROM to_warehouse_id",
            name="ck_stock_movements_no_self_transfer",
        ),
        Index("ix_stock_movements_product_created", "product_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    movement_type: Mapped[MovementType] = mapped_column(
        Enum(MovementType, native_enum=False, validate_strings=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(nullable=False)
    from_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    to_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    performed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped[Product] = relationship()
    from_warehouse: Mapped[Warehouse | None] = relationship(foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped[Warehouse | None] = relationship(foreign_keys=[to_warehouse_id])
    performed_by: Mapped[User] = relationship()
