from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def get(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def create(db: Session, payload: SupplierCreate) -> Supplier:
    return common.create(db, Supplier, payload)


def update(db: Session, supplier: Supplier, payload: SupplierUpdate) -> Supplier:
    return common.update(db, supplier, payload)


def soft_delete(db: Session, supplier: Supplier) -> None:
    common.soft_delete(db, supplier)


def list_suppliers(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Supplier], int]:
    stmt = select(Supplier).order_by(Supplier.id)
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
