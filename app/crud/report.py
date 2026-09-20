from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.customer import Customer
from app.models.customer_order import CustomerOrder, CustomerOrderLine
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.shipment import Shipment, ShipmentLine
from app.models.stock import Stock
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse


def _date_range(
    column: ColumnElement, date_from: datetime | None, date_to: datetime | None
) -> list[ColumnElement]:
    conditions = [column.isnot(None)]
    if date_from is not None:
        conditions.append(column >= date_from)
    if date_to is not None:
        conditions.append(column <= date_to)
    return conditions


def stock_valuation(db: Session, *, warehouse_id: int | None = None, category_id: int | None = None) -> dict:
    filters = []
    if warehouse_id is not None:
        filters.append(Stock.warehouse_id == warehouse_id)
    if category_id is not None:
        filters.append(Product.category_id == category_id)

    warehouse_stmt = (
        select(
            Warehouse,
            func.coalesce(func.sum(Stock.quantity * Product.unit_price), 0),
            func.coalesce(func.sum(Stock.quantity), 0),
        )
        .select_from(Stock)
        .join(Product, Stock.product_id == Product.id)
        .join(Warehouse, Stock.warehouse_id == Warehouse.id)
        .where(*filters)
        .group_by(Warehouse.id)
        .order_by(Warehouse.name)
    )
    by_warehouse = [
        {"warehouse": warehouse, "total_value": value, "total_quantity": quantity}
        for warehouse, value, quantity in db.execute(warehouse_stmt).all()
    ]

    category_stmt = (
        select(
            Category,
            func.coalesce(func.sum(Stock.quantity * Product.unit_price), 0),
            func.coalesce(func.sum(Stock.quantity), 0),
        )
        .select_from(Stock)
        .join(Product, Stock.product_id == Product.id)
        .join(Category, Product.category_id == Category.id)
        .where(*filters)
        .group_by(Category.id)
        .order_by(Category.name)
    )
    by_category = [
        {"category": category, "total_value": value, "total_quantity": quantity}
        for category, value, quantity in db.execute(category_stmt).all()
    ]

    total_value = sum((row["total_value"] for row in by_warehouse), Decimal("0"))
    total_quantity = sum((row["total_quantity"] for row in by_warehouse), 0)

    return {
        "total_value": total_value,
        "total_quantity": total_quantity,
        "by_warehouse": by_warehouse,
        "by_category": by_category,
    }


def purchase_activity(
    db: Session, *, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    submitted_stmt = (
        select(PurchaseOrder.supplier_id, func.count(PurchaseOrder.id))
        .where(*_date_range(PurchaseOrder.submitted_at, date_from, date_to))
        .group_by(PurchaseOrder.supplier_id)
    )
    submitted_by_supplier = dict(db.execute(submitted_stmt).all())

    # A PO's individual receive events aren't separately timestamped (only the order's aggregate
    # received_at) - "received in range" approximates to orders whose most recent (full) receipt
    # landed in the range, with the *line's* cumulative quantity_received/value counted whole.
    received_stmt = (
        select(
            PurchaseOrder.supplier_id,
            func.count(func.distinct(PurchaseOrder.id)),
            func.coalesce(func.sum(PurchaseOrderLine.quantity_received * PurchaseOrderLine.unit_price), 0),
        )
        .join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
        .where(*_date_range(PurchaseOrder.received_at, date_from, date_to))
        .group_by(PurchaseOrder.supplier_id)
    )
    received_by_supplier = {
        supplier_id: (count, value) for supplier_id, count, value in db.execute(received_stmt).all()
    }

    supplier_ids = set(submitted_by_supplier) | set(received_by_supplier)
    rows = []
    for supplier_id in supplier_ids:
        received_count, received_value = received_by_supplier.get(supplier_id, (0, Decimal("0")))
        rows.append(
            {
                "supplier": db.get(Supplier, supplier_id),
                "orders_submitted": submitted_by_supplier.get(supplier_id, 0),
                "orders_received": received_count,
                "received_value": received_value,
            }
        )
    rows.sort(key=lambda row: row["supplier"].name)
    return rows


def sales_fulfillment_activity(
    db: Session, *, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[dict]:
    confirmed_stmt = (
        select(CustomerOrder.customer_id, func.count(CustomerOrder.id))
        .where(*_date_range(CustomerOrder.confirmed_at, date_from, date_to))
        .group_by(CustomerOrder.customer_id)
    )
    confirmed_by_customer = dict(db.execute(confirmed_stmt).all())

    # Shipment.created_at is when stock actually left (see shipment_service.create_shipment), so
    # that - not shipped_at/delivered_at - is what "shipped in range" is measured against.
    shipped_stmt = (
        select(
            CustomerOrder.customer_id,
            func.count(func.distinct(Shipment.id)),
            func.coalesce(func.sum(ShipmentLine.quantity * CustomerOrderLine.unit_price), 0),
        )
        .select_from(Shipment)
        .join(CustomerOrder, Shipment.customer_order_id == CustomerOrder.id)
        .join(ShipmentLine, ShipmentLine.shipment_id == Shipment.id)
        .join(CustomerOrderLine, ShipmentLine.customer_order_line_id == CustomerOrderLine.id)
        .where(*_date_range(Shipment.created_at, date_from, date_to))
        .group_by(CustomerOrder.customer_id)
    )
    shipped_by_customer = {
        customer_id: (count, value) for customer_id, count, value in db.execute(shipped_stmt).all()
    }

    customer_ids = set(confirmed_by_customer) | set(shipped_by_customer)
    rows = []
    for customer_id in customer_ids:
        shipments_created, shipped_value = shipped_by_customer.get(customer_id, (0, Decimal("0")))
        rows.append(
            {
                "customer": db.get(Customer, customer_id),
                "orders_confirmed": confirmed_by_customer.get(customer_id, 0),
                "shipments_created": shipments_created,
                "shipped_value": shipped_value,
            }
        )
    rows.sort(key=lambda row: row["customer"].name)
    return rows
