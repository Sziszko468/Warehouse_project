from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


def get(db: Session, warehouse_id: int) -> Warehouse | None:
    return db.get(Warehouse, warehouse_id)


def get_by_name(db: Session, name: str) -> Warehouse | None:
    return db.scalar(select(Warehouse).where(Warehouse.name == name))


def create(db: Session, payload: WarehouseCreate) -> Warehouse:
    return common.create(db, Warehouse, payload)


def update(db: Session, warehouse: Warehouse, payload: WarehouseUpdate) -> Warehouse:
    return common.update(db, warehouse, payload)


def soft_delete(db: Session, warehouse: Warehouse) -> None:
    common.soft_delete(db, warehouse)


def list_warehouses(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Warehouse], int]:
    stmt = select(Warehouse).order_by(Warehouse.id)
    if not include_inactive:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
