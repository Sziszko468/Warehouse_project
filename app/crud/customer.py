from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


def get(db: Session, customer_id: int) -> Customer | None:
    return db.get(Customer, customer_id)


def create(db: Session, payload: CustomerCreate, *, performed_by_id: int) -> Customer:
    return common.create(db, Customer, payload, performed_by_id=performed_by_id)


def update(db: Session, customer: Customer, payload: CustomerUpdate, *, performed_by_id: int) -> Customer:
    return common.update(db, customer, payload, performed_by_id=performed_by_id)


def soft_delete(db: Session, customer: Customer, *, performed_by_id: int) -> None:
    common.soft_delete(db, customer, performed_by_id=performed_by_id)


def list_customers(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Customer], int]:
    stmt = select(Customer).order_by(Customer.id)
    if not include_inactive:
        stmt = stmt.where(Customer.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
