"""Populate the database with electronics-wholesaler demo data. Run with: uv run python -m app.seed

Safe to run more than once: existing categories/suppliers/warehouses/products (matched by their
unique field) and existing stock levels are left untouched rather than duplicated.
"""

from sqlalchemy import select

from app.config import settings
from app.crud import category as crud_category
from app.crud import product as crud_product
from app.crud import supplier as crud_supplier
from app.crud import user as crud_user
from app.crud import warehouse as crud_warehouse
from app.database import SessionLocal
from app.models.stock import Stock
from app.models.user import UserRole
from app.schemas.category import CategoryCreate
from app.schemas.product import ProductCreate
from app.schemas.supplier import SupplierCreate
from app.schemas.warehouse import WarehouseCreate
from app.services import stock_service

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
                category = crud_category.create(db, CategoryCreate(name=name, description=description))
            category_ids[name] = category.id

        supplier_ids = []
        existing_suppliers, _ = crud_supplier.list_suppliers(db, include_inactive=True, limit=200)
        existing_supplier_by_name = {s.name: s for s in existing_suppliers}
        for name, contact_name, email, phone in SUPPLIERS:
            supplier = existing_supplier_by_name.get(name)
            if supplier is None:
                supplier = crud_supplier.create(
                    db, SupplierCreate(name=name, contact_name=contact_name, email=email, phone=phone)
                )
            supplier_ids.append(supplier.id)

        warehouse_ids = {}
        for name, address in WAREHOUSES:
            warehouse = crud_warehouse.get_by_name(db, name)
            if warehouse is None:
                warehouse = crud_warehouse.create(db, WarehouseCreate(name=name, address=address))
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
                )
            product_ids[sku] = product.id

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

        db.commit()
        print(
            f"Seed complete: {len(category_ids)} categories, {len(supplier_ids)} suppliers, "
            f"{len(warehouse_ids)} warehouses, {len(product_ids)} products, {stock_ins} new stock-in movements."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
