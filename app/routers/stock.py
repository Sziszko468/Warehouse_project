from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.crud import stock as crud_stock
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User
from app.models.warehouse import Warehouse
from app.routers.csv_helpers import EXPORT_ROW_LIMIT, csv_response
from app.schemas.common import Page
from app.schemas.stock import LowStockRead, StockRead
from app.schemas.stock_movement import StockInCreate, StockMovementRead, StockOutCreate, StockTransferCreate
from app.services import email_service, stock_service

router = APIRouter(prefix="/stock", tags=["stock"])


def _schedule_low_stock_check_if_crossed(
    background_tasks: BackgroundTasks, db: Session, *, product_id: int, warehouse_id: int, quantity_before: int
) -> None:
    """Compares stock before/after a stock/out or transfer call and schedules a low-stock email
    only on the downward crossing (was above the threshold, now at-or-below it) - so repeated
    stock/out calls while already low don't re-notify every time."""
    product = db.get(Product, product_id)
    threshold = product.min_stock_threshold if product is not None else 0
    if quantity_before <= threshold:
        return
    quantity_after = crud_stock.get_quantity(db, product_id, warehouse_id)
    if quantity_after > threshold:
        return
    warehouse = db.get(Warehouse, warehouse_id)
    background_tasks.add_task(
        email_service.notify_low_stock,
        product_name=product.name if product is not None else f"#{product_id}",
        warehouse_name=warehouse.name if warehouse is not None else f"#{warehouse_id}",
        quantity=quantity_after,
        threshold=threshold,
    )


@router.get("", response_model=Page[StockRead])
def list_stock(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[StockRead]:
    items, total = crud_stock.list_stock(
        db, product_id=product_id, warehouse_id=warehouse_id, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/export")
def export_stock(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, _total = crud_stock.list_stock(
        db, product_id=product_id, warehouse_id=warehouse_id, limit=EXPORT_ROW_LIMIT, offset=0
    )
    rows = [
        [s.id, s.product.sku, s.product.name, s.warehouse.name, s.quantity, s.reserved_quantity, s.updated_at]
        for s in items
    ]
    return csv_response(
        "stock.csv",
        ["id", "product_sku", "product_name", "warehouse", "quantity", "reserved_quantity", "updated_at"],
        rows,
    )


@router.get("/low-stock", response_model=Page[LowStockRead])
def low_stock(
    warehouse_id: int | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[LowStockRead]:
    items, total = crud_stock.list_low_stock(
        db, warehouse_id=warehouse_id, limit=pagination.limit, offset=pagination.offset
    )
    enriched = [
        LowStockRead(
            id=s.id,
            product=s.product,
            warehouse=s.warehouse,
            quantity=s.quantity,
            reserved_quantity=s.reserved_quantity,
            updated_at=s.updated_at,
            min_stock_threshold=s.product.min_stock_threshold,
        )
        for s in items
    ]
    return Page(items=enriched, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/movements", response_model=Page[StockMovementRead])
def list_movements(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    movement_type: MovementType | None = None,
    performed_by_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[StockMovementRead]:
    items, total = crud_stock.list_movements(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/movements/export")
def export_movements(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    movement_type: MovementType | None = None,
    performed_by_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, _total = crud_stock.list_movements(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
        limit=EXPORT_ROW_LIMIT,
        offset=0,
    )
    rows = [
        [
            m.id,
            m.created_at,
            m.product.sku,
            m.product.name,
            m.movement_type.value,
            m.quantity,
            m.from_warehouse.name if m.from_warehouse else "",
            m.to_warehouse.name if m.to_warehouse else "",
            m.performed_by.full_name,
            m.note or "",
        ]
        for m in items
    ]
    return csv_response(
        "stock_movements.csv",
        [
            "id",
            "created_at",
            "product_sku",
            "product_name",
            "movement_type",
            "quantity",
            "from_warehouse",
            "to_warehouse",
            "performed_by",
            "note",
        ],
        rows,
    )


@router.post("/in", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def stock_in(
    payload: StockInCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> StockMovement:
    return stock_service.stock_in(
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by_id=current_user.id,
    )


@router.post("/out", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def stock_out(
    payload: StockOutCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StockMovement:
    quantity_before = crud_stock.get_quantity(db, payload.product_id, payload.warehouse_id)
    movement = stock_service.stock_out(
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by_id=current_user.id,
    )
    _schedule_low_stock_check_if_crossed(
        background_tasks,
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        quantity_before=quantity_before,
    )
    return movement


@router.post("/transfer", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def transfer(
    payload: StockTransferCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StockMovement:
    quantity_before = crud_stock.get_quantity(db, payload.product_id, payload.from_warehouse_id)
    movement = stock_service.transfer(
        db,
        product_id=payload.product_id,
        from_warehouse_id=payload.from_warehouse_id,
        to_warehouse_id=payload.to_warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by_id=current_user.id,
    )
    _schedule_low_stock_check_if_crossed(
        background_tasks,
        db,
        product_id=payload.product_id,
        warehouse_id=payload.from_warehouse_id,
        quantity_before=quantity_before,
    )
    return movement
