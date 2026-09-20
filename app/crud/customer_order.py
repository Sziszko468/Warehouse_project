from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud.common import paginate, update
from app.models.customer_order import CustomerOrder, CustomerOrderLine, CustomerOrderStatus
from app.schemas.customer_order import CustomerOrderUpdate

_EAGER_OPTIONS = (
    selectinload(CustomerOrder.lines).joinedload(CustomerOrderLine.product),
    joinedload(CustomerOrder.customer),
    joinedload(CustomerOrder.warehouse),
    joinedload(CustomerOrder.created_by),
)


def get(db: Session, customer_order_id: int) -> CustomerOrder | None:
    stmt = select(CustomerOrder).where(CustomerOrder.id == customer_order_id).options(*_EAGER_OPTIONS)
    return db.scalar(stmt)


def get_line_locked(db: Session, customer_order_id: int, line_id: int) -> CustomerOrderLine | None:
    """Row-locks an order line for the rest of this transaction, used by shipment_service so
    concurrent shipments against the same line can't race on quantity_shipped."""
    stmt = (
        select(CustomerOrderLine)
        .where(CustomerOrderLine.id == line_id, CustomerOrderLine.customer_order_id == customer_order_id)
        .with_for_update()
    )
    return db.scalar(stmt)


def create(db: Session, customer_order: CustomerOrder) -> CustomerOrder:
    db.add(customer_order)
    db.flush()
    db.refresh(customer_order)
    return get(db, customer_order.id)  # type: ignore[return-value]


def update_notes(db: Session, customer_order: CustomerOrder, payload: CustomerOrderUpdate) -> CustomerOrder:
    return update(db, customer_order, payload)


def list_customer_orders(
    db: Session,
    *,
    status: CustomerOrderStatus | None = None,
    customer_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[CustomerOrder], int]:
    stmt = (
        select(CustomerOrder)
        .options(*_EAGER_OPTIONS)
        .order_by(CustomerOrder.created_at.desc(), CustomerOrder.id.desc())
    )
    if status is not None:
        stmt = stmt.where(CustomerOrder.status == status)
    if customer_id is not None:
        stmt = stmt.where(CustomerOrder.customer_id == customer_id)
    if warehouse_id is not None:
        stmt = stmt.where(CustomerOrder.warehouse_id == warehouse_id)
    if date_from is not None:
        stmt = stmt.where(CustomerOrder.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(CustomerOrder.created_at <= date_to)
    return paginate(db, stmt, limit=limit, offset=offset)
