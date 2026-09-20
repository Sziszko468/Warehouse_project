from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.crud import customer_order as crud_customer_order
from app.exceptions import InsufficientStockError, InvalidOrderStateError, NotFoundError
from app.messages import Messages
from app.models.audit_log import AuditAction
from app.models.customer import Customer
from app.models.customer_order import CustomerOrder, CustomerOrderLine, CustomerOrderStatus
from app.models.product import Product
from app.models.warehouse import Warehouse
from app.schemas.customer_order import CustomerOrderCreate
from app.services import audit_service, stock_service


def _require_customer(db: Session, customer_id: int) -> None:
    customer = db.get(Customer, customer_id)
    if customer is None or not customer.is_active:
        raise NotFoundError(Messages.CUSTOMER_NOT_FOUND)


def _require_warehouse(db: Session, warehouse_id: int) -> None:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise NotFoundError(Messages.WAREHOUSE_NOT_FOUND)


def _require_active_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError(Messages.PRODUCT_NOT_FOUND)
    return product


def _recompute_shipping_status(order: CustomerOrder) -> None:
    if all(line.quantity_shipped >= line.quantity_ordered for line in order.lines):
        order.status = CustomerOrderStatus.SHIPPED
        order.shipped_at = order.shipped_at or datetime.now(UTC)
    elif any(line.quantity_shipped > 0 for line in order.lines):
        order.status = CustomerOrderStatus.PARTIALLY_SHIPPED
        order.shipped_at = None
    else:
        order.status = CustomerOrderStatus.CONFIRMED
        order.shipped_at = None


def create_customer_order(db: Session, payload: CustomerOrderCreate, *, created_by_id: int) -> CustomerOrder:
    _require_customer(db, payload.customer_id)
    _require_warehouse(db, payload.warehouse_id)

    lines = []
    for line in payload.lines:
        product = _require_active_product(db, line.product_id)
        lines.append(
            CustomerOrderLine(
                product_id=line.product_id, quantity_ordered=line.quantity_ordered, unit_price=product.unit_price
            )
        )

    customer_order = CustomerOrder(
        customer_id=payload.customer_id,
        warehouse_id=payload.warehouse_id,
        notes=payload.notes,
        created_by_id=created_by_id,
        status=CustomerOrderStatus.DRAFT,
        lines=lines,
    )
    created = crud_customer_order.create(db, customer_order)
    audit_service.record(
        db,
        entity_type="CustomerOrder",
        entity_id=created.id,
        action=AuditAction.CREATE,
        performed_by_id=created_by_id,
    )
    return created


def confirm_customer_order(db: Session, order: CustomerOrder, *, performed_by_id: int) -> CustomerOrder:
    if order.status != CustomerOrderStatus.DRAFT:
        raise InvalidOrderStateError(Messages.CUSTOMER_ORDER_NOT_DRAFT)

    # Lock every line's stock row in a deterministic order (ascending product_id) before
    # validating any of them, so two concurrent confirms touching an overlapping product set
    # can't deadlock on each other - same technique stock_service.transfer uses for its two
    # warehouse locks.
    locked_stocks = {}
    for line in sorted(order.lines, key=lambda line: line.product_id):
        stock = stock_service.get_or_create_stock_locked(db, line.product_id, order.warehouse_id)
        available = stock.quantity - stock.reserved_quantity
        if available < line.quantity_ordered:
            raise InsufficientStockError(Messages.insufficient_stock(line.quantity_ordered, available))
        locked_stocks[line.id] = stock

    # Only reserve once every line has been proven available - an order that can't be fully
    # reserved reserves nothing at all.
    for line in order.lines:
        locked_stocks[line.id].reserved_quantity += line.quantity_ordered

    order.status = CustomerOrderStatus.CONFIRMED
    order.confirmed_at = datetime.now(UTC)
    db.flush()
    db.refresh(order)
    audit_service.record(
        db,
        entity_type="CustomerOrder",
        entity_id=order.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="confirmed",
    )
    return order


def cancel_customer_order(db: Session, order: CustomerOrder, *, performed_by_id: int) -> CustomerOrder:
    if order.status not in (CustomerOrderStatus.DRAFT, CustomerOrderStatus.CONFIRMED):
        raise InvalidOrderStateError(Messages.CUSTOMER_ORDER_CANNOT_CANCEL)

    if order.status == CustomerOrderStatus.CONFIRMED:
        for line in order.lines:
            stock = stock_service.get_stock_locked(db, line.product_id, order.warehouse_id)
            assert stock is not None, "reserved stock row must exist for a confirmed order line"
            stock.reserved_quantity -= line.quantity_ordered

    order.status = CustomerOrderStatus.CANCELLED
    order.cancelled_at = datetime.now(UTC)
    db.flush()
    db.refresh(order)
    audit_service.record(
        db,
        entity_type="CustomerOrder",
        entity_id=order.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="cancelled",
    )
    return order


def apply_shipment(db: Session, order: CustomerOrder, shipped_by_line: dict[int, int]) -> None:
    """Called by shipment_service after it has already moved the physical/reserved stock -
    updates order/line bookkeeping only."""
    for line in order.lines:
        quantity = shipped_by_line.get(line.id)
        if quantity:
            line.quantity_shipped += quantity
    _recompute_shipping_status(order)
    db.flush()
    db.refresh(order)


def revert_shipment(db: Session, order: CustomerOrder, shipped_by_line: dict[int, int]) -> None:
    """Symmetric undo for shipment cancellation - called by shipment_service after it has already
    reversed the physical/reserved stock."""
    for line in order.lines:
        quantity = shipped_by_line.get(line.id)
        if quantity:
            line.quantity_shipped -= quantity
    _recompute_shipping_status(order)
    db.flush()
    db.refresh(order)
