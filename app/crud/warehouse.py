from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.common import paginate
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


def get(db: Session, warehouse_id: int) -> Warehouse | None:
    return db.get(Warehouse, warehouse_id)


def get_by_name(db: Session, name: str) -> Warehouse | None:
    return db.scalar(select(Warehouse).where(Warehouse.name == name))


def create(db: Session, payload: WarehouseCreate) -> Warehouse:
    warehouse = Warehouse(**payload.model_dump())
    db.add(warehouse)
    db.flush()
    db.refresh(warehouse)
    return warehouse


def update(db: Session, warehouse: Warehouse, payload: WarehouseUpdate) -> Warehouse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    db.flush()
    db.refresh(warehouse)
    return warehouse


def soft_delete(db: Session, warehouse: Warehouse) -> None:
    warehouse.is_active = False
    db.flush()


def list_warehouses(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Warehouse], int]:
    stmt = select(Warehouse).order_by(Warehouse.id)
    if not include_inactive:
        stmt = stmt.where(Warehouse.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
