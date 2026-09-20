from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def get(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_by_sku(db: Session, sku: str) -> Product | None:
    return db.scalar(select(Product).where(Product.sku == sku))


def create(db: Session, payload: ProductCreate, *, performed_by_id: int) -> Product:
    return common.create(db, Product, payload, performed_by_id=performed_by_id)


def update(db: Session, product: Product, payload: ProductUpdate, *, performed_by_id: int) -> Product:
    return common.update(db, product, payload, performed_by_id=performed_by_id)


def soft_delete(db: Session, product: Product, *, performed_by_id: int) -> None:
    common.soft_delete(db, product, performed_by_id=performed_by_id)


def list_products(
    db: Session,
    *,
    include_inactive: bool = False,
    category_id: int | None = None,
    supplier_id: int | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Product], int]:
    stmt = select(Product).order_by(Product.id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if supplier_id is not None:
        stmt = stmt.where(Product.supplier_id == supplier_id)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Product.name.ilike(pattern), Product.sku.ilike(pattern)))
    return paginate(db, stmt, limit=limit, offset=offset)
