from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.crud import customer_order as crud_customer_order
from app.crud import shipment as crud_shipment
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.customer_order import CustomerOrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.shipment import ShipmentCreate, ShipmentRead
from app.services import email_service, shipment_service

router = APIRouter(prefix="/shipments", tags=["shipments"])


@router.get("", response_model=Page[ShipmentRead])
def list_shipments(
    customer_order_id: int | None = None,
    status: ShipmentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[ShipmentRead]:
    items, total = crud_shipment.list_shipments(
        db,
        customer_order_id=customer_order_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{shipment_id}", response_model=ShipmentRead)
def get_shipment(shipment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Shipment:
    return get_or_404(crud_shipment.get, db, shipment_id, Messages.SHIPMENT_NOT_FOUND)


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
def create_shipment(
    payload: ShipmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Shipment:
    result = shipment_service.create_shipment(db, payload, created_by_id=current_user.id)
    order = crud_customer_order.get(db, result.customer_order_id)
    if order is not None and order.status == CustomerOrderStatus.SHIPPED:
        background_tasks.add_task(
            email_service.notify_customer_order_shipped,
            customer_order_id=order.id,
            customer_name=order.customer.name,
        )
    return result


@router.patch("/{shipment_id}/dispatch", response_model=ShipmentRead)
def dispatch_shipment(
    shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Shipment:
    shipment = get_or_404(crud_shipment.get, db, shipment_id, Messages.SHIPMENT_NOT_FOUND)
    return shipment_service.dispatch_shipment(db, shipment, performed_by_id=current_user.id)


@router.patch("/{shipment_id}/deliver", response_model=ShipmentRead)
def deliver_shipment(
    shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Shipment:
    shipment = get_or_404(crud_shipment.get, db, shipment_id, Messages.SHIPMENT_NOT_FOUND)
    return shipment_service.deliver_shipment(db, shipment, performed_by_id=current_user.id)


@router.post("/{shipment_id}/cancel", response_model=ShipmentRead)
def cancel_shipment(
    shipment_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> Shipment:
    shipment = get_or_404(crud_shipment.get, db, shipment_id, Messages.SHIPMENT_NOT_FOUND)
    return shipment_service.cancel_shipment(db, shipment, performed_by_id=current_user.id)
