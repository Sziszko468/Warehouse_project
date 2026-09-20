from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud import customer_order as crud_customer_order
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user
from app.messages import Messages
from app.models.customer_order import CustomerOrder, CustomerOrderStatus
from app.models.user import User
from app.routers.csv_helpers import EXPORT_ROW_LIMIT, csv_response
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.customer_order import CustomerOrderCreate, CustomerOrderRead, CustomerOrderUpdate
from app.services import customer_order_service

router = APIRouter(prefix="/customer-orders", tags=["customer-orders"])


@router.get("", response_model=Page[CustomerOrderRead])
def list_customer_orders(
    status: CustomerOrderStatus | None = None,
    customer_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[CustomerOrderRead]:
    items, total = crud_customer_order.list_customer_orders(
        db,
        status=status,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/export")
def export_customer_orders(
    status: CustomerOrderStatus | None = None,
    customer_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, _total = crud_customer_order.list_customer_orders(
        db,
        status=status,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
        limit=EXPORT_ROW_LIMIT,
        offset=0,
    )
    rows = [
        [
            co.id,
            co.customer.name,
            co.warehouse.name,
            co.status.value,
            co.created_at,
            co.confirmed_at or "",
            co.shipped_at or "",
            co.cancelled_at or "",
            co.notes or "",
        ]
        for co in items
    ]
    return csv_response(
        "customer_orders.csv",
        [
            "id",
            "customer",
            "warehouse",
            "status",
            "created_at",
            "confirmed_at",
            "shipped_at",
            "cancelled_at",
            "notes",
        ],
        rows,
    )


@router.get("/{customer_order_id}", response_model=CustomerOrderRead)
def get_customer_order(
    customer_order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> CustomerOrder:
    return get_or_404(crud_customer_order.get, db, customer_order_id, Messages.CUSTOMER_ORDER_NOT_FOUND)


@router.post("", response_model=CustomerOrderRead, status_code=status.HTTP_201_CREATED)
def create_customer_order(
    payload: CustomerOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CustomerOrder:
    return customer_order_service.create_customer_order(db, payload, created_by_id=current_user.id)


@router.patch("/{customer_order_id}", response_model=CustomerOrderRead)
def update_customer_order(
    customer_order_id: int,
    payload: CustomerOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CustomerOrder:
    order = get_or_404(crud_customer_order.get, db, customer_order_id, Messages.CUSTOMER_ORDER_NOT_FOUND)
    return crud_customer_order.update_notes(db, order, payload)


@router.post("/{customer_order_id}/confirm", response_model=CustomerOrderRead)
def confirm_customer_order(
    customer_order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CustomerOrder:
    order = get_or_404(crud_customer_order.get, db, customer_order_id, Messages.CUSTOMER_ORDER_NOT_FOUND)
    return customer_order_service.confirm_customer_order(db, order, performed_by_id=current_user.id)


@router.post("/{customer_order_id}/cancel", response_model=CustomerOrderRead)
def cancel_customer_order(
    customer_order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> CustomerOrder:
    order = get_or_404(crud_customer_order.get, db, customer_order_id, Messages.CUSTOMER_ORDER_NOT_FOUND)
    return customer_order_service.cancel_customer_order(db, order, performed_by_id=current_user.id)
