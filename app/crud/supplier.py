from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def get(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def create(db: Session, payload: SupplierCreate, *, performed_by_id: int) -> Supplier:
    return common.create(db, Supplier, payload, performed_by_id=performed_by_id)


def update(db: Session, supplier: Supplier, payload: SupplierUpdate, *, performed_by_id: int) -> Supplier:
    return common.update(db, supplier, payload, performed_by_id=performed_by_id)


def soft_delete(db: Session, supplier: Supplier, *, performed_by_id: int) -> None:
    common.soft_delete(db, supplier, performed_by_id=performed_by_id)


def list_suppliers(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Supplier], int]:
    stmt = select(Supplier).order_by(Supplier.id)
    if not include_inactive:
        stmt = stmt.where(Supplier.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
