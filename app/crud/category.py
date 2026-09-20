from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import common
from app.crud.common import paginate
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def get(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == name))


def create(db: Session, payload: CategoryCreate, *, performed_by_id: int) -> Category:
    return common.create(db, Category, payload, performed_by_id=performed_by_id)


def update(db: Session, category: Category, payload: CategoryUpdate, *, performed_by_id: int) -> Category:
    return common.update(db, category, payload, performed_by_id=performed_by_id)


def soft_delete(db: Session, category: Category, *, performed_by_id: int) -> None:
    common.soft_delete(db, category, performed_by_id=performed_by_id)


def list_categories(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Category], int]:
    stmt = select(Category).order_by(Category.id)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
