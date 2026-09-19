from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import stock as crud_stock
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User
from app.schemas.common import Page
from app.schemas.stock import LowStockRead, StockRead
from app.schemas.stock_movement import StockInCreate, StockMovementRead, StockOutCreate, StockTransferCreate
from app.services import stock_service

router = APIRouter(prefix="/stock", tags=["stock"])


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
    payload: StockOutCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> StockMovement:
    return stock_service.stock_out(
        db,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by_id=current_user.id,
    )


@router.post("/transfer", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def transfer(
    payload: StockTransferCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> StockMovement:
    return stock_service.transfer(
        db,
        product_id=payload.product_id,
        from_warehouse_id=payload.from_warehouse_id,
        to_warehouse_id=payload.to_warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by_id=current_user.id,
    )
