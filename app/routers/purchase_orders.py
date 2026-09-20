from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.crud import purchase_order as crud_purchase_order
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.user import User
from app.routers.csv_helpers import EXPORT_ROW_LIMIT, csv_response
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderReceiveRequest,
    PurchaseOrderUpdate,
)
from app.services import email_service, purchase_order_service

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


@router.get("", response_model=Page[PurchaseOrderRead])
def list_purchase_orders(
    status: PurchaseOrderStatus | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[PurchaseOrderRead]:
    items, total = crud_purchase_order.list_purchase_orders(
        db,
        status=status,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/export")
def export_purchase_orders(
    status: PurchaseOrderStatus | None = None,
    supplier_id: int | None = None,
    warehouse_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, _total = crud_purchase_order.list_purchase_orders(
        db,
        status=status,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        date_from=date_from,
        date_to=date_to,
        limit=EXPORT_ROW_LIMIT,
        offset=0,
    )
    rows = [
        [
            po.id,
            po.supplier.name,
            po.warehouse.name,
            po.status.value,
            po.created_at,
            po.submitted_at or "",
            po.received_at or "",
            po.cancelled_at or "",
            po.notes or "",
        ]
        for po in items
    ]
    return csv_response(
        "purchase_orders.csv",
        [
            "id",
            "supplier",
            "warehouse",
            "status",
            "created_at",
            "submitted_at",
            "received_at",
            "cancelled_at",
            "notes",
        ],
        rows,
    )


@router.get("/{purchase_order_id}", response_model=PurchaseOrderRead)
def get_purchase_order(
    purchase_order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> PurchaseOrder:
    return get_or_404(crud_purchase_order.get, db, purchase_order_id, Messages.PURCHASE_ORDER_NOT_FOUND)


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> PurchaseOrder:
    return purchase_order_service.create_purchase_order(db, payload, created_by_id=current_user.id)


@router.patch("/{purchase_order_id}", response_model=PurchaseOrderRead)
def update_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> PurchaseOrder:
    purchase_order = get_or_404(crud_purchase_order.get, db, purchase_order_id, Messages.PURCHASE_ORDER_NOT_FOUND)
    return crud_purchase_order.update_notes(db, purchase_order, payload)


@router.post("/{purchase_order_id}/submit", response_model=PurchaseOrderRead)
def submit_purchase_order(
    purchase_order_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> PurchaseOrder:
    purchase_order = get_or_404(crud_purchase_order.get, db, purchase_order_id, Messages.PURCHASE_ORDER_NOT_FOUND)
    result = purchase_order_service.submit_purchase_order(db, purchase_order, performed_by_id=current_user.id)
    background_tasks.add_task(
        email_service.notify_purchase_order_submitted,
        purchase_order_id=result.id,
        supplier_name=result.supplier.name,
    )
    return result


@router.post("/{purchase_order_id}/cancel", response_model=PurchaseOrderRead)
def cancel_purchase_order(
    purchase_order_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> PurchaseOrder:
    purchase_order = get_or_404(crud_purchase_order.get, db, purchase_order_id, Messages.PURCHASE_ORDER_NOT_FOUND)
    return purchase_order_service.cancel_purchase_order(db, purchase_order, performed_by_id=current_user.id)


@router.post("/{purchase_order_id}/receive", response_model=PurchaseOrderRead)
def receive_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderReceiveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PurchaseOrder:
    purchase_order = get_or_404(crud_purchase_order.get, db, purchase_order_id, Messages.PURCHASE_ORDER_NOT_FOUND)
    result = purchase_order_service.receive_purchase_order(
        db, purchase_order, lines=payload.lines, note=payload.note, performed_by_id=current_user.id
    )
    if result.status == PurchaseOrderStatus.RECEIVED:
        background_tasks.add_task(
            email_service.notify_purchase_order_received,
            purchase_order_id=result.id,
            supplier_name=result.supplier.name,
        )
    return result
