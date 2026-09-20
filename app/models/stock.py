from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.product import Product
from app.models.warehouse import Warehouse


class Stock(Base, TimestampMixin):
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_stock_product_warehouse"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_stock_reserved_quantity_non_negative"),
        # backstop for the invariant stock_service/customer_order_service maintain: a confirmed
        # customer order can only reserve quantity that's actually physically present.
        CheckConstraint("reserved_quantity <= quantity", name="ck_stock_reserved_quantity_not_over_physical"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    # quantity held for confirmed-but-not-yet-shipped customer order lines against this
    # (product, warehouse) - see customer_order_service.confirm_customer_order/cancel_customer_order
    # and shipment_service, which are the only writers of this column.
    reserved_quantity: Mapped[int] = mapped_column(default=0, nullable=False)

    product: Mapped[Product] = relationship()
    warehouse: Mapped[Warehouse] = relationship()
