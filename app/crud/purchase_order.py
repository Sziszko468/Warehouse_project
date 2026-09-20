from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud.common import paginate, update
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus
from app.schemas.purchase_order import PurchaseOrderUpdate

_EAGER_OPTIONS = (
    selectinload(PurchaseOrder.lines).joinedload(PurchaseOrderLine.product),
    joinedload(PurchaseOrder.supplier),
    joinedload(PurchaseOrder.warehouse),
    joinedload(PurchaseOrder.created_by),
)


def get(db: Session, purchase_order_id: int) -> PurchaseOrder | None:
    stmt = select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id).options(*_EAGER_OPTIONS)
    return db.scalar(stmt)


def get_line_locked(db: Session, purchase_order_id: int, line_id: int) -> PurchaseOrderLine | None:
    """Row-locks a PO line for the rest of this transaction, used by the receive flow."""
    stmt = (
        select(PurchaseOrderLine)
        .where(PurchaseOrderLine.id == line_id, PurchaseOrderLine.purchase_order_id == purchase_order_id)
        .with_for_update()
    )
    return db.scalar(stmt)


def create(db: Session, purchase_order: PurchaseOrder) -> PurchaseOrder:
    db.add(purchase_order)
    db.flush()
    db.refresh(purchase_order)
    return get(db, purchase_order.id)  # type: ignore[return-value]


def update_notes(db: Session, purchase_order: PurchaseOrder, payload: PurchaseOrderUpdate) -> PurchaseOrder:
    return update(db, purchase_order, payload)


def list_purchase_orders(
    db: Session,
    *,
    status: PurchaseOrderStatus | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PurchaseOrder], int]:
    stmt = (
        select(PurchaseOrder)
        .options(*_EAGER_OPTIONS)
        .order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc())
    )
    if status is not None:
        stmt = stmt.where(PurchaseOrder.status == status)
    if supplier_id is not None:
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
    if warehouse_id is not None:
        stmt = stmt.where(PurchaseOrder.warehouse_id == warehouse_id)
    if date_from is not None:
        stmt = stmt.where(PurchaseOrder.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(PurchaseOrder.created_at <= date_to)
    return paginate(db, stmt, limit=limit, offset=offset)
