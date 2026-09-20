from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.crud import customer_order as crud_customer_order
from app.crud import shipment as crud_shipment
from app.exceptions import InvalidOrderStateError, NotFoundError
from app.messages import Messages
from app.models.audit_log import AuditAction
from app.models.customer_order import CustomerOrder, CustomerOrderLine, CustomerOrderStatus
from app.models.shipment import Shipment, ShipmentLine, ShipmentStatus
from app.schemas.shipment import ShipmentCreate
from app.services import audit_service, customer_order_service, stock_service


def create_shipment(db: Session, payload: ShipmentCreate, *, created_by_id: int) -> Shipment:
    order = crud_customer_order.get(db, payload.customer_order_id)
    if order is None:
        raise NotFoundError(Messages.CUSTOMER_ORDER_NOT_FOUND)
    if order.status not in (CustomerOrderStatus.CONFIRMED, CustomerOrderStatus.PARTIALLY_SHIPPED):
        raise InvalidOrderStateError(Messages.SHIPMENT_ORDER_NOT_SHIPPABLE)

    order_lines_by_id: dict[int, CustomerOrderLine] = {line.id: line for line in order.lines}
    for requested in payload.lines:
        if requested.customer_order_line_id not in order_lines_by_id:
            raise NotFoundError(Messages.SHIPMENT_LINE_NOT_ON_ORDER)

    # Lock in a deterministic order (ascending product_id) across both the order lines and the
    # stock rows below, mirroring confirm_customer_order/transfer's deadlock-avoidance technique.
    sorted_requests = sorted(
        payload.lines, key=lambda requested: order_lines_by_id[requested.customer_order_line_id].product_id
    )

    locked_lines: dict[int, CustomerOrderLine] = {}
    for requested in sorted_requests:
        line = crud_customer_order.get_line_locked(db, order.id, requested.customer_order_line_id)
        assert line is not None
        remaining = line.quantity_ordered - line.quantity_shipped
        if requested.quantity > remaining:
            raise InvalidOrderStateError(Messages.over_shipment(requested.quantity, remaining))
        locked_lines[requested.customer_order_line_id] = line

    shipment = Shipment(
        customer_order_id=order.id,
        carrier=payload.carrier,
        tracking_number=payload.tracking_number,
        created_by_id=created_by_id,
        status=ShipmentStatus.PENDING,
        lines=[
            ShipmentLine(customer_order_line_id=req.customer_order_line_id, quantity=req.quantity)
            for req in payload.lines
        ],
    )
    db.add(shipment)
    db.flush()

    shipped_by_line: dict[int, int] = {}
    for requested in sorted_requests:
        line = locked_lines[requested.customer_order_line_id]
        # Release this order's hold on exactly the amount now physically leaving, *before*
        # stock_out's availability check runs, so it correctly sees that quantity as available.
        stock = stock_service.get_stock_locked(db, line.product_id, order.warehouse_id)
        assert stock is not None, "reserved stock row must exist for a confirmed order line"
        stock.reserved_quantity -= requested.quantity
        stock_service.stock_out(
            db,
            product_id=line.product_id,
            warehouse_id=order.warehouse_id,
            quantity=requested.quantity,
            note=f"Shipment #{shipment.id} for CO #{order.id}",
            performed_by_id=created_by_id,
        )
        shipped_by_line[line.id] = shipped_by_line.get(line.id, 0) + requested.quantity

    customer_order_service.apply_shipment(db, order, shipped_by_line)

    db.refresh(shipment)
    audit_service.record(
        db, entity_type="Shipment", entity_id=shipment.id, action=AuditAction.CREATE, performed_by_id=created_by_id
    )
    return crud_shipment.get(db, shipment.id)  # type: ignore[return-value]


def dispatch_shipment(db: Session, shipment: Shipment, *, performed_by_id: int) -> Shipment:
    if shipment.status != ShipmentStatus.PENDING:
        raise InvalidOrderStateError(Messages.SHIPMENT_NOT_PENDING)
    shipment.status = ShipmentStatus.IN_TRANSIT
    shipment.shipped_at = datetime.now(UTC)
    db.flush()
    db.refresh(shipment)
    audit_service.record(
        db,
        entity_type="Shipment",
        entity_id=shipment.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="dispatched",
    )
    return shipment


def deliver_shipment(db: Session, shipment: Shipment, *, performed_by_id: int) -> Shipment:
    if shipment.status != ShipmentStatus.IN_TRANSIT:
        raise InvalidOrderStateError(Messages.SHIPMENT_NOT_IN_TRANSIT)
    shipment.status = ShipmentStatus.DELIVERED
    shipment.delivered_at = datetime.now(UTC)
    db.flush()
    db.refresh(shipment)
    audit_service.record(
        db,
        entity_type="Shipment",
        entity_id=shipment.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="delivered",
    )
    return shipment


def cancel_shipment(db: Session, shipment: Shipment, *, performed_by_id: int) -> Shipment:
    if shipment.status not in (ShipmentStatus.PENDING, ShipmentStatus.IN_TRANSIT):
        raise InvalidOrderStateError(Messages.SHIPMENT_CANNOT_CANCEL)

    order: CustomerOrder | None = crud_customer_order.get(db, shipment.customer_order_id)
    assert order is not None

    shipped_by_line: dict[int, int] = {}
    for line in sorted(shipment.lines, key=lambda line: line.customer_order_line.product_id):
        product_id = line.customer_order_line.product_id
        stock_service.stock_in(
            db,
            product_id=product_id,
            warehouse_id=order.warehouse_id,
            quantity=line.quantity,
            note=f"Shipment #{shipment.id} cancelled — stock reversal",
            performed_by_id=performed_by_id,
        )
        # The order still expects to ship this quantity later (cancelling the shipment doesn't
        # cancel the order) - re-reserve it now that it's physically back in stock.
        stock = stock_service.get_stock_locked(db, product_id, order.warehouse_id)
        assert stock is not None
        stock.reserved_quantity += line.quantity
        shipped_by_line[line.customer_order_line_id] = (
            shipped_by_line.get(line.customer_order_line_id, 0) + line.quantity
        )

    customer_order_service.revert_shipment(db, order, shipped_by_line)

    shipment.status = ShipmentStatus.CANCELLED
    db.flush()
    db.refresh(shipment)
    audit_service.record(
        db,
        entity_type="Shipment",
        entity_id=shipment.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="cancelled",
    )
    return shipment
