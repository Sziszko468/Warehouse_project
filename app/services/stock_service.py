from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import InsufficientStockError, InvalidStockOperationError, NotFoundError
from app.messages import Messages
from app.models.product import Product
from app.models.stock import Stock
from app.models.stock_movement import MovementType, StockMovement
from app.models.warehouse import Warehouse


def _require_product(db: Session, product_id: int) -> None:
    # Soft-deleted counts as not-found here too (see products.py's _validate_references) - a
    # discontinued product shouldn't silently keep accruing new stock movements.
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise NotFoundError(Messages.PRODUCT_NOT_FOUND)


def _require_warehouse(db: Session, warehouse_id: int) -> None:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None or not warehouse.is_active:
        raise NotFoundError(Messages.WAREHOUSE_NOT_FOUND)


def _get_stock_locked(db: Session, product_id: int, warehouse_id: int) -> Stock | None:
    """Row-locks the (product, warehouse) stock row for the rest of this transaction, if it exists."""
    return db.scalar(
        select(Stock).where(Stock.product_id == product_id, Stock.warehouse_id == warehouse_id).with_for_update()
    )


def _get_or_create_stock_locked(db: Session, product_id: int, warehouse_id: int) -> Stock:
    stock = _get_stock_locked(db, product_id, warehouse_id)
    if stock is not None:
        return stock
    # SAVEPOINT: if a concurrent request wins the race to create this same row first, only
    # this insert attempt unwinds (not the whole request transaction) and we re-fetch+lock it.
    try:
        with db.begin_nested():
            stock = Stock(product_id=product_id, warehouse_id=warehouse_id, quantity=0)
            db.add(stock)
            db.flush()
    except IntegrityError:
        stock = _get_stock_locked(db, product_id, warehouse_id)
        assert stock is not None
    return stock


def stock_in(
    db: Session, *, product_id: int, warehouse_id: int, quantity: int, note: str | None, performed_by_id: int
) -> StockMovement:
    _require_product(db, product_id)
    _require_warehouse(db, warehouse_id)

    stock = _get_or_create_stock_locked(db, product_id, warehouse_id)
    stock.quantity += quantity

    movement = StockMovement(
        product_id=product_id,
        movement_type=MovementType.IN,
        quantity=quantity,
        to_warehouse_id=warehouse_id,
        note=note,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.flush()
    db.refresh(movement)
    return movement


def stock_out(
    db: Session, *, product_id: int, warehouse_id: int, quantity: int, note: str | None, performed_by_id: int
) -> StockMovement:
    _require_product(db, product_id)
    _require_warehouse(db, warehouse_id)

    stock = _get_stock_locked(db, product_id, warehouse_id)
    available = stock.quantity if stock is not None else 0
    if available < quantity:
        raise InsufficientStockError(Messages.insufficient_stock(quantity, available))
    stock.quantity -= quantity

    movement = StockMovement(
        product_id=product_id,
        movement_type=MovementType.OUT,
        quantity=quantity,
        from_warehouse_id=warehouse_id,
        note=note,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.flush()
    db.refresh(movement)
    return movement


def transfer(
    db: Session,
    *,
    product_id: int,
    from_warehouse_id: int,
    to_warehouse_id: int,
    quantity: int,
    note: str | None,
    performed_by_id: int,
) -> StockMovement:
    if from_warehouse_id == to_warehouse_id:
        raise InvalidStockOperationError(Messages.SELF_TRANSFER_REJECTED)

    _require_product(db, product_id)
    _require_warehouse(db, from_warehouse_id)
    _require_warehouse(db, to_warehouse_id)

    # Lock both rows in a deterministic order (ascending warehouse_id), independent of which
    # side is "from" and which is "to" — otherwise two opposite-direction transfers of the same
    # product between the same two warehouses could each hold one lock and wait on the other.
    first_id, second_id = sorted([from_warehouse_id, to_warehouse_id])
    locked = {
        first_id: _get_or_create_stock_locked(db, product_id, first_id),
        second_id: _get_or_create_stock_locked(db, product_id, second_id),
    }
    from_stock = locked[from_warehouse_id]
    to_stock = locked[to_warehouse_id]

    if from_stock.quantity < quantity:
        raise InsufficientStockError(Messages.insufficient_stock(quantity, from_stock.quantity))

    from_stock.quantity -= quantity
    to_stock.quantity += quantity

    movement = StockMovement(
        product_id=product_id,
        movement_type=MovementType.TRANSFER,
        quantity=quantity,
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        note=note,
        performed_by_id=performed_by_id,
    )
    db.add(movement)
    db.flush()
    db.refresh(movement)
    return movement
