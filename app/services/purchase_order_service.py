from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.crud import purchase_order as crud_purchase_order
from app.exceptions import InvalidOrderStateError, NotFoundError
from app.messages import Messages
from app.models.audit_log import AuditAction
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine, PurchaseOrderStatus
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderReceiveLine
from app.services import audit_service, stock_service


def _require_supplier(db: Session, supplier_id: int) -> None:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or not supplier.is_active:
        raise NotFoundError(Messages.SUPPLIER_NOT_FOUND)


def _require_warehouse(db: Session, warehouse_id: int) -> None:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise NotFoundError(Messages.WAREHOUSE_NOT_FOUND)


def _require_product(db: Session, product_id: int) -> None:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError(Messages.PRODUCT_NOT_FOUND)


def create_purchase_order(db: Session, payload: PurchaseOrderCreate, *, created_by_id: int) -> PurchaseOrder:
    _require_supplier(db, payload.supplier_id)
    _require_warehouse(db, payload.warehouse_id)
    for line in payload.lines:
        _require_product(db, line.product_id)

    purchase_order = PurchaseOrder(
        supplier_id=payload.supplier_id,
        warehouse_id=payload.warehouse_id,
        notes=payload.notes,
        created_by_id=created_by_id,
        status=PurchaseOrderStatus.DRAFT,
        lines=[
            PurchaseOrderLine(
                product_id=line.product_id, quantity_ordered=line.quantity_ordered, unit_price=line.unit_price
            )
            for line in payload.lines
        ],
    )
    created = crud_purchase_order.create(db, purchase_order)
    audit_service.record(
        db,
        entity_type="PurchaseOrder",
        entity_id=created.id,
        action=AuditAction.CREATE,
        performed_by_id=created_by_id,
    )
    return created


def submit_purchase_order(db: Session, purchase_order: PurchaseOrder, *, performed_by_id: int) -> PurchaseOrder:
    if purchase_order.status != PurchaseOrderStatus.DRAFT:
        raise InvalidOrderStateError(Messages.PURCHASE_ORDER_NOT_DRAFT)
    purchase_order.status = PurchaseOrderStatus.SUBMITTED
    purchase_order.submitted_at = datetime.now(UTC)
    db.flush()
    db.refresh(purchase_order)
    audit_service.record(
        db,
        entity_type="PurchaseOrder",
        entity_id=purchase_order.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="submitted",
    )
    return purchase_order


def cancel_purchase_order(db: Session, purchase_order: PurchaseOrder, *, performed_by_id: int) -> PurchaseOrder:
    if purchase_order.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.SUBMITTED):
        raise InvalidOrderStateError(Messages.PURCHASE_ORDER_CANNOT_CANCEL)
    purchase_order.status = PurchaseOrderStatus.CANCELLED
    purchase_order.cancelled_at = datetime.now(UTC)
    db.flush()
    db.refresh(purchase_order)
    audit_service.record(
        db,
        entity_type="PurchaseOrder",
        entity_id=purchase_order.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary="cancelled",
    )
    return purchase_order


def receive_purchase_order(
    db: Session,
    purchase_order: PurchaseOrder,
    *,
    lines: list[PurchaseOrderReceiveLine],
    note: str | None,
    performed_by_id: int,
) -> PurchaseOrder:
    if purchase_order.status not in (PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.PARTIALLY_RECEIVED):
        raise InvalidOrderStateError(Messages.PURCHASE_ORDER_NOT_RECEIVABLE)

    movement_note = f"Received against PO #{purchase_order.id}" + (f" — {note}" if note else "")
    for requested in lines:
        line = crud_purchase_order.get_line_locked(db, purchase_order.id, requested.purchase_order_line_id)
        if line is None:
            raise NotFoundError(Messages.PURCHASE_ORDER_LINE_NOT_FOUND)
        remaining = line.quantity_ordered - line.quantity_received
        if requested.quantity > remaining:
            raise InvalidOrderStateError(Messages.over_receipt(requested.quantity, remaining))

        stock_service.stock_in(
            db,
            product_id=line.product_id,
            warehouse_id=purchase_order.warehouse_id,
            quantity=requested.quantity,
            note=movement_note,
            performed_by_id=performed_by_id,
        )
        line.quantity_received += requested.quantity

    db.flush()
    db.refresh(purchase_order)
    if all(line.quantity_received >= line.quantity_ordered for line in purchase_order.lines):
        purchase_order.status = PurchaseOrderStatus.RECEIVED
        purchase_order.received_at = datetime.now(UTC)
    else:
        purchase_order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
    db.flush()
    db.refresh(purchase_order)
    audit_service.record(
        db,
        entity_type="PurchaseOrder",
        entity_id=purchase_order.id,
        action=AuditAction.STATUS_CHANGE,
        performed_by_id=performed_by_id,
        summary=f"received ({purchase_order.status.value})",
    )
    return purchase_order
