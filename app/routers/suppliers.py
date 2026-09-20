from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import supplier as crud_supplier
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.supplier import Supplier
from app.models.user import User
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=Page[SupplierRead])
def list_suppliers(
    include_inactive: bool = False,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[SupplierRead]:
    items, total = crud_supplier.list_suppliers(
        db, include_inactive=include_inactive, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Supplier:
    return get_or_404(crud_supplier.get, db, supplier_id, Messages.SUPPLIER_NOT_FOUND)


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> Supplier:
    return crud_supplier.create(db, payload, performed_by_id=current_user.id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Supplier:
    supplier = get_or_404(crud_supplier.get, db, supplier_id, Messages.SUPPLIER_NOT_FOUND)
    return crud_supplier.update(db, supplier, payload, performed_by_id=current_user.id)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> None:
    supplier = get_or_404(crud_supplier.get, db, supplier_id, Messages.SUPPLIER_NOT_FOUND)
    crud_supplier.soft_delete(db, supplier, performed_by_id=current_user.id)
