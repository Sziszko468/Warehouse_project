from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.crud.common import paginate
from app.models.product import Product
from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement


def get_quantity(db: Session, product_id: int, warehouse_id: int) -> int:
    stock = db.scalar(select(Stock).where(Stock.product_id == product_id, Stock.warehouse_id == warehouse_id))
    return stock.quantity if stock is not None else 0


def list_stock(
    db: Session,
    *,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Stock], int]:
    stmt = select(Stock).options(joinedload(Stock.product), joinedload(Stock.warehouse)).order_by(Stock.id)
    if product_id is not None:
        stmt = stmt.where(Stock.product_id == product_id)
    if warehouse_id is not None:
        stmt = stmt.where(Stock.warehouse_id == warehouse_id)
    return paginate(db, stmt, limit=limit, offset=offset)


def list_low_stock(
    db: Session, *, warehouse_id: int | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[Stock], int]:
    stmt = (
        select(Stock)
        .join(Product, Stock.product_id == Product.id)
        .where(Stock.quantity <= Product.min_stock_threshold)
        .options(contains_eager(Stock.product), joinedload(Stock.warehouse))
        .order_by(Stock.id)
    )
    if warehouse_id is not None:
        stmt = stmt.where(Stock.warehouse_id == warehouse_id)
    return paginate(db, stmt, limit=limit, offset=offset)


def list_movements(
    db: Session,
    *,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    movement_type: MovementType | None = None,
    performed_by_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[StockMovement], int]:
    stmt = (
        select(StockMovement)
        .options(
            joinedload(StockMovement.product),
            joinedload(StockMovement.from_warehouse),
            joinedload(StockMovement.to_warehouse),
            joinedload(StockMovement.performed_by),
        )
        # id is the tie-breaker: two movements can land on the same created_at at typical
        # timestamp precision (e.g. a rapid sequence of calls), and without a deterministic
        # secondary key their relative order in the result would be undefined.
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    )
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if warehouse_id is not None:
        stmt = stmt.where(
            or_(StockMovement.from_warehouse_id == warehouse_id, StockMovement.to_warehouse_id == warehouse_id)
        )
    if movement_type is not None:
        stmt = stmt.where(StockMovement.movement_type == movement_type)
    if performed_by_id is not None:
        stmt = stmt.where(StockMovement.performed_by_id == performed_by_id)
    if date_from is not None:
        stmt = stmt.where(StockMovement.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(StockMovement.created_at <= date_to)
    return paginate(db, stmt, limit=limit, offset=offset)
