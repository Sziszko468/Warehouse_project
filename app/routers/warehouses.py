from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import warehouse as crud_warehouse
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.common import Page
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=Page[WarehouseRead])
def list_warehouses(
    include_inactive: bool = False,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[WarehouseRead]:
    items, total = crud_warehouse.list_warehouses(
        db, include_inactive=include_inactive, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{warehouse_id}", response_model=WarehouseRead)
def get_warehouse(
    warehouse_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> Warehouse:
    warehouse = crud_warehouse.get(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    return warehouse


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    payload: WarehouseCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Warehouse:
    if crud_warehouse.get_by_name(db, payload.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Warehouse name already exists")
    return crud_warehouse.create(db, payload)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: int, payload: WarehouseUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Warehouse:
    warehouse = crud_warehouse.get(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    if (
        payload.name
        and payload.name != warehouse.name
        and crud_warehouse.get_by_name(db, payload.name) is not None
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Warehouse name already exists")
    return crud_warehouse.update(db, warehouse, payload)


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(warehouse_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> None:
    warehouse = crud_warehouse.get(db, warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")
    crud_warehouse.soft_delete(db, warehouse)
