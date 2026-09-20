from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import customer as crud_customer
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.customer import Customer
from app.models.user import User
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerRead])
def list_customers(
    include_inactive: bool = False,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[CustomerRead]:
    items, total = crud_customer.list_customers(
        db, include_inactive=include_inactive, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Customer:
    return get_or_404(crud_customer.get, db, customer_id, Messages.CUSTOMER_NOT_FOUND)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> Customer:
    return crud_customer.create(db, payload, performed_by_id=current_user.id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Customer:
    customer = get_or_404(crud_customer.get, db, customer_id, Messages.CUSTOMER_NOT_FOUND)
    return crud_customer.update(db, customer, payload, performed_by_id=current_user.id)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> None:
    customer = get_or_404(crud_customer.get, db, customer_id, Messages.CUSTOMER_NOT_FOUND)
    crud_customer.soft_delete(db, customer, performed_by_id=current_user.id)
