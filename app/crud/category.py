from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.common import paginate
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def get(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == name))


def create(db: Session, payload: CategoryCreate) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    db.flush()
    db.refresh(category)
    return category


def update(db: Session, category: Category, payload: CategoryUpdate) -> Category:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.flush()
    db.refresh(category)
    return category


def soft_delete(db: Session, category: Category) -> None:
    category.is_active = False
    db.flush()


def list_categories(
    db: Session, *, include_inactive: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Category], int]:
    stmt = select(Category).order_by(Category.id)
    if not include_inactive:
        stmt = stmt.where(Category.is_active.is_(True))
    return paginate(db, stmt, limit=limit, offset=offset)
