from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.crud.common import paginate, update
from app.models.customer_order import CustomerOrderLine
from app.models.shipment import Shipment, ShipmentLine, ShipmentStatus
from app.schemas.shipment import ShipmentUpdate

_EAGER_OPTIONS = (
    selectinload(Shipment.lines)
    .joinedload(ShipmentLine.customer_order_line)
    .joinedload(CustomerOrderLine.product),
    joinedload(Shipment.created_by),
)


def get(db: Session, shipment_id: int) -> Shipment | None:
    stmt = select(Shipment).where(Shipment.id == shipment_id).options(*_EAGER_OPTIONS)
    return db.scalar(stmt)


def create(db: Session, shipment: Shipment) -> Shipment:
    db.add(shipment)
    db.flush()
    db.refresh(shipment)
    return get(db, shipment.id)  # type: ignore[return-value]


def update_carrier_info(db: Session, shipment: Shipment, payload: ShipmentUpdate) -> Shipment:
    return update(db, shipment, payload)


def list_shipments(
    db: Session,
    *,
    customer_order_id: int | None = None,
    status: ShipmentStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Shipment], int]:
    stmt = select(Shipment).options(*_EAGER_OPTIONS).order_by(Shipment.created_at.desc(), Shipment.id.desc())
    if customer_order_id is not None:
        stmt = stmt.where(Shipment.customer_order_id == customer_order_id)
    if status is not None:
        stmt = stmt.where(Shipment.status == status)
    if date_from is not None:
        stmt = stmt.where(Shipment.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Shipment.created_at <= date_to)
    return paginate(db, stmt, limit=limit, offset=offset)
