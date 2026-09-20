"""Populate the database with electronics-wholesaler demo data. Run with: uv run python -m app.seed

Safe to run more than once: existing categories/suppliers/warehouses/products (matched by their
unique field) and existing stock levels are left untouched rather than duplicated.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import category as crud_category
from app.crud import customer as crud_customer
from app.crud import customer_order as crud_customer_order
from app.crud import product as crud_product
from app.crud import purchase_order as crud_purchase_order
from app.crud import supplier as crud_supplier
from app.crud import user as crud_user
from app.crud import warehouse as crud_warehouse
from app.database import SessionLocal
from app.models.stock import Stock
from app.models.user import UserRole
from app.schemas.category import CategoryCreate
from app.schemas.customer import CustomerCreate
from app.schemas.customer_order import CustomerOrderCreate, CustomerOrderLineCreate
from app.schemas.product import ProductCreate
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderLineCreate, PurchaseOrderReceiveLine
from app.schemas.shipment import ShipmentCreate, ShipmentLineCreate
from app.schemas.supplier import SupplierCreate
from app.schemas.warehouse import WarehouseCreate
from app.services import customer_order_service, purchase_order_service, shipment_service, stock_service

CATEGORIES = [
    ("Cables", "Cables and connectors"),
    ("Networking Equipment", "Routers, switches, and networking gear"),
    ("Monitors", "Computer monitors and displays"),
    ("Components", "Internal PC components"),
    ("Peripherals", "Keyboards, mice, and other peripherals"),
]

SUPPLIERS = [
    ("TechDistribute Kft.", "Anna Kovacs", "sales@techdistribute.example", "+36-1-555-0100"),
    ("NordicParts AB", "Erik Larsson", "orders@nordicparts.example", "+46-8-555-0199"),
]

WAREHOUSES = [
    ("Budapest Central", "1097 Budapest, Konyves Kalman krt. 12"),
    ("Debrecen Depot", "4025 Debrecen, Piac utca 45"),
]

# sku, name, category, supplier index (into SUPPLIERS), unit_price, min_stock_threshold
PRODUCTS = [
    ("CBL-USB-C-1M", "USB-C Cable 1m", "Cables", 0, "4.99", 50),
    ("CBL-HDMI-2M", "HDMI Cable 2m", "Cables", 0, "8.49", 30),
    ("NET-SW-24P", "24-Port Gigabit Switch", "Networking Equipment", 1, "129.00", 5),
    ("NET-RT-AX", "Wi-Fi 6 Router", "Networking Equipment", 1, "89.90", 10),
    ("MON-27-4K", "27-inch 4K Monitor", "Monitors", 0, "349.00", 8),
    ("MON-24-FHD", "24-inch FHD Monitor", "Monitors", 0, "159.00", 12),
    ("CMP-SSD-1TB", "1TB NVMe SSD", "Components", 1, "79.99", 25),
    ("CMP-RAM-16GB", "16GB DDR5 RAM Module", "Components", 1, "54.50", 20),
    ("PRF-KB-MECH", "Mechanical Keyboard", "Peripherals", 0, "69.00", 15),
    ("PRF-MS-WL", "Wireless Mouse", "Peripherals", 0, "24.90", 20),
]

CUSTOMERS = [
    ("Kovács Kereskedés Kft.", "Kovács Béla", "info@kovacskereskedes.example", "+36-1-555-0200"),
    ("Nagy Elektronika Bt.", "Nagy Éva", "orders@nagyelektronika.example", "+36-1-555-0210"),
    ("PixelTech Zrt.", "Szabó Márk", "purchasing@pixeltech.example", "+36-1-555-0220"),
    ("Debrecen IT Solutions Kft.", "Tóth Gábor", "info@debrecenit.example", "+36-52-555-0230"),
]

# sku -> {warehouse name: initial quantity}. NET-SW-24P is deliberately left below its
# threshold (5) to give the low-stock endpoint something to report out of the box.
INITIAL_STOCK = {
    "CBL-USB-C-1M": {"Budapest Central": 200, "Debrecen Depot": 80},
    "CBL-HDMI-2M": {"Budapest Central": 120},
    "NET-SW-24P": {"Budapest Central": 3},
    "NET-RT-AX": {"Budapest Central": 40, "Debrecen Depot": 15},
    "MON-27-4K": {"Budapest Central": 20},
    "MON-24-FHD": {"Budapest Central": 35, "Debrecen Depot": 10},
    "CMP-SSD-1TB": {"Budapest Central": 60},
    "CMP-RAM-16GB": {"Budapest Central": 45},
    "PRF-KB-MECH": {"Budapest Central": 30},
    "PRF-MS-WL": {"Budapest Central": 50, "Debrecen Depot": 20},
}


def _seed_demo_orders(
    db: Session,
    *,
    admin_id: int,
    product_ids: dict[str, int],
    warehouse_ids: dict[str, int],
    supplier_ids: list[int],
    customer_ids: list[int],
) -> tuple[int, int, int]:
    """Adds a demo batch of purchase orders, customer orders, and shipments spanning every
    lifecycle status, so the new order/shipment pages and reports have something to show.

    Only runs while the database has few enough purchase/customer orders that this looks like the
    initial demo dataset rather than a real, organically-grown one - re-running the seed script
    won't pile up duplicate demo orders once that baseline exists.
    """
    _, existing_po_total = crud_purchase_order.list_purchase_orders(db, limit=1)
    _, existing_co_total = crud_customer_order.list_customer_orders(db, limit=1)
    if existing_po_total >= 5 and existing_co_total >= 5:
        return 0, 0, 0

    bp = warehouse_ids["Budapest Central"]
    debrecen = warehouse_ids["Debrecen Depot"]
    tech_distribute, nordic_parts = supplier_ids[0], supplier_ids[1]
    kovacs, nagy, pixeltech, debrecen_it = customer_ids[0], customer_ids[1], customer_ids[2], customer_ids[3]

    po_count = 0

    # 1. Fully received
    po = purchase_order_service.create_purchase_order(
        db,
        PurchaseOrderCreate(
            supplier_id=nordic_parts,
            warehouse_id=bp,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=product_ids["NET-RT-AX"], quantity_ordered=20, unit_price="62.00"
                ),
                PurchaseOrderLineCreate(
                    product_id=product_ids["CMP-RAM-16GB"], quantity_ordered=30, unit_price="38.00"
                ),
            ],
        ),
        created_by_id=admin_id,
    )
    po = purchase_order_service.submit_purchase_order(db, po, performed_by_id=admin_id)
    po = purchase_order_service.receive_purchase_order(
        db,
        po,
        lines=[
            PurchaseOrderReceiveLine(purchase_order_line_id=line.id, quantity=line.quantity_ordered)
            for line in po.lines
        ],
        note="Demo seed - full delivery",
        performed_by_id=admin_id,
    )
    po_count += 1

    # 2. Partially received (restocks the deliberately-low NET-SW-24P)
    po = purchase_order_service.create_purchase_order(
        db,
        PurchaseOrderCreate(
            supplier_id=tech_distribute,
            warehouse_id=bp,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=product_ids["NET-SW-24P"], quantity_ordered=15, unit_price="95.00"
                )
            ],
        ),
        created_by_id=admin_id,
    )
    po = purchase_order_service.submit_purchase_order(db, po, performed_by_id=admin_id)
    purchase_order_service.receive_purchase_order(
        db,
        po,
        lines=[PurchaseOrderReceiveLine(purchase_order_line_id=po.lines[0].id, quantity=8)],
        note="Demo seed - partial delivery",
        performed_by_id=admin_id,
    )
    po_count += 1

    # 3. Submitted, not yet received
    po = purchase_order_service.create_purchase_order(
        db,
        PurchaseOrderCreate(
            supplier_id=nordic_parts,
            warehouse_id=debrecen,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=product_ids["MON-24-FHD"], quantity_ordered=10, unit_price="115.00"
                )
            ],
        ),
        created_by_id=admin_id,
    )
    purchase_order_service.submit_purchase_order(db, po, performed_by_id=admin_id)
    po_count += 1

    # 4. Draft
    purchase_order_service.create_purchase_order(
        db,
        PurchaseOrderCreate(
            supplier_id=tech_distribute,
            warehouse_id=bp,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=product_ids["PRF-KB-MECH"], quantity_ordered=25, unit_price="45.00"
                )
            ],
        ),
        created_by_id=admin_id,
    )
    po_count += 1

    # 5. Cancelled
    po = purchase_order_service.create_purchase_order(
        db,
        PurchaseOrderCreate(
            supplier_id=nordic_parts,
            warehouse_id=bp,
            lines=[
                PurchaseOrderLineCreate(
                    product_id=product_ids["CMP-SSD-1TB"], quantity_ordered=10, unit_price="55.00"
                )
            ],
        ),
        created_by_id=admin_id,
    )
    purchase_order_service.submit_purchase_order(db, po, performed_by_id=admin_id)
    purchase_order_service.cancel_purchase_order(db, po, performed_by_id=admin_id)
    po_count += 1

    co_count = 0
    shipment_count = 0

    def _confirmed_order(customer_id: int, sku: str, quantity: int):
        nonlocal co_count
        order = customer_order_service.create_customer_order(
            db,
            CustomerOrderCreate(
                customer_id=customer_id,
                warehouse_id=bp,
                lines=[CustomerOrderLineCreate(product_id=product_ids[sku], quantity_ordered=quantity)],
            ),
            created_by_id=admin_id,
        )
        co_count += 1
        return customer_order_service.confirm_customer_order(db, order, performed_by_id=admin_id)

    # 1. Draft only
    customer_order_service.create_customer_order(
        db,
        CustomerOrderCreate(
            customer_id=nagy,
            warehouse_id=bp,
            lines=[
                CustomerOrderLineCreate(product_id=product_ids["CBL-USB-C-1M"], quantity_ordered=20),
                CustomerOrderLineCreate(product_id=product_ids["PRF-MS-WL"], quantity_ordered=5),
            ],
        ),
        created_by_id=admin_id,
    )
    co_count += 1

    # 2. Confirmed only (stock reserved, not yet shipped)
    _confirmed_order(pixeltech, "MON-27-4K", 3)

    # 3. Partially shipped - one pending shipment covering part of the order
    order = _confirmed_order(debrecen_it, "CMP-SSD-1TB", 10)
    line_id = order.lines[0].id
    shipment_service.create_shipment(
        db,
        ShipmentCreate(
            customer_order_id=order.id,
            carrier="GLS",
            lines=[ShipmentLineCreate(customer_order_line_id=line_id, quantity=4)],
        ),
        created_by_id=admin_id,
    )
    shipment_count += 1

    # 4. Fully shipped and delivered
    order = _confirmed_order(nagy, "PRF-KB-MECH", 8)
    shipment = shipment_service.create_shipment(
        db,
        ShipmentCreate(
            customer_order_id=order.id,
            carrier="DPD",
            tracking_number="DPD-DEMO-0001",
            lines=[ShipmentLineCreate(customer_order_line_id=order.lines[0].id, quantity=8)],
        ),
        created_by_id=admin_id,
    )
    shipment = shipment_service.dispatch_shipment(db, shipment, performed_by_id=admin_id)
    shipment_service.deliver_shipment(db, shipment, performed_by_id=admin_id)
    shipment_count += 1

    # 5. Confirmed, then cancelled before shipping
    order = _confirmed_order(pixeltech, "CBL-HDMI-2M", 15)
    customer_order_service.cancel_customer_order(db, order, performed_by_id=admin_id)

    # 6. Fully shipped, in transit (not yet delivered)
    order = _confirmed_order(debrecen_it, "CMP-RAM-16GB", 6)
    shipment = shipment_service.create_shipment(
        db,
        ShipmentCreate(
            customer_order_id=order.id,
            carrier="FedEx",
            lines=[ShipmentLineCreate(customer_order_line_id=order.lines[0].id, quantity=6)],
        ),
        created_by_id=admin_id,
    )
    shipment_service.dispatch_shipment(db, shipment, performed_by_id=admin_id)
    shipment_count += 1

    # 7. Shipment created then cancelled (stock/reservation reversed) - order stays confirmed
    order = _confirmed_order(nagy, "NET-RT-AX", 5)
    shipment = shipment_service.create_shipment(
        db,
        ShipmentCreate(
            customer_order_id=order.id,
            carrier="GLS",
            lines=[ShipmentLineCreate(customer_order_line_id=order.lines[0].id, quantity=5)],
        ),
        created_by_id=admin_id,
    )
    shipment_service.cancel_shipment(db, shipment, performed_by_id=admin_id)
    shipment_count += 1

    # 8. Another confirmed-but-unshipped order, for the customer created via the app earlier
    _confirmed_order(kovacs, "CBL-USB-C-1M", 10)

    return po_count, co_count, shipment_count


def run() -> None:
    db = SessionLocal()
    try:
        admin = crud_user.get_by_email(db, settings.first_admin_email)
        if admin is None:
            admin = crud_user.create_user(
                db,
                email=settings.first_admin_email,
                password=settings.first_admin_password,
                full_name="Admin",
                role=UserRole.ADMIN,
            )

        category_ids = {}
        for name, description in CATEGORIES:
            category = crud_category.get_by_name(db, name)
            if category is None:
                category = crud_category.create(
                    db, CategoryCreate(name=name, description=description), performed_by_id=admin.id
                )
            category_ids[name] = category.id

        supplier_ids = []
        existing_suppliers, _ = crud_supplier.list_suppliers(db, include_inactive=True, limit=200)
        existing_supplier_by_name = {s.name: s for s in existing_suppliers}
        for name, contact_name, email, phone in SUPPLIERS:
            supplier = existing_supplier_by_name.get(name)
            if supplier is None:
                supplier = crud_supplier.create(
                    db,
                    SupplierCreate(name=name, contact_name=contact_name, email=email, phone=phone),
                    performed_by_id=admin.id,
                )
            supplier_ids.append(supplier.id)

        warehouse_ids = {}
        for name, address in WAREHOUSES:
            warehouse = crud_warehouse.get_by_name(db, name)
            if warehouse is None:
                warehouse = crud_warehouse.create(
                    db, WarehouseCreate(name=name, address=address), performed_by_id=admin.id
                )
            warehouse_ids[name] = warehouse.id

        product_ids = {}
        for sku, name, category_name, supplier_idx, unit_price, threshold in PRODUCTS:
            product = crud_product.get_by_sku(db, sku)
            if product is None:
                product = crud_product.create(
                    db,
                    ProductCreate(
                        sku=sku,
                        name=name,
                        category_id=category_ids[category_name],
                        supplier_id=supplier_ids[supplier_idx],
                        unit_price=unit_price,
                        min_stock_threshold=threshold,
                    ),
                    performed_by_id=admin.id,
                )
            product_ids[sku] = product.id

        customer_ids = []
        existing_customers, _ = crud_customer.list_customers(db, include_inactive=True, limit=200)
        existing_customer_by_name = {c.name: c for c in existing_customers}
        for name, contact_name, email, phone in CUSTOMERS:
            customer = existing_customer_by_name.get(name)
            if customer is None:
                customer = crud_customer.create(
                    db,
                    CustomerCreate(name=name, contact_name=contact_name, email=email, phone=phone),
                    performed_by_id=admin.id,
                )
            customer_ids.append(customer.id)

        stock_ins = 0
        for sku, warehouse_quantities in INITIAL_STOCK.items():
            for warehouse_name, quantity in warehouse_quantities.items():
                product_id = product_ids[sku]
                warehouse_id = warehouse_ids[warehouse_name]
                already_stocked = db.scalar(
                    select(Stock).where(Stock.product_id == product_id, Stock.warehouse_id == warehouse_id)
                )
                if already_stocked is not None:
                    continue
                stock_service.stock_in(
                    db,
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=quantity,
                    note="Initial seed stock",
                    performed_by_id=admin.id,
                )
                stock_ins += 1

        po_count, co_count, shipment_count = _seed_demo_orders(
            db,
            admin_id=admin.id,
            product_ids=product_ids,
            warehouse_ids=warehouse_ids,
            supplier_ids=supplier_ids,
            customer_ids=customer_ids,
        )

        db.commit()
        print(
            f"Seed complete: {len(category_ids)} categories, {len(supplier_ids)} suppliers, "
            f"{len(customer_ids)} customers, {len(warehouse_ids)} warehouses, {len(product_ids)} products, "
            f"{stock_ins} new stock-in movements, {po_count} purchase orders, {co_count} customer orders, "
            f"{shipment_count} shipments."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
