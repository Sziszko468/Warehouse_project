from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def paginate(db: Session, stmt: Select, *, limit: int, offset: int) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.limit(limit).offset(offset)).all()
    return list(items), total


def create[ModelT](db: Session, model_cls: type[ModelT], payload: BaseModel) -> ModelT:
    obj = model_cls(**payload.model_dump())
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return obj


def update[ModelT](db: Session, obj: ModelT, payload: BaseModel) -> ModelT:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.flush()
    db.refresh(obj)
    return obj


class _HasIsActive(Protocol):
    is_active: bool


def soft_delete(db: Session, obj: _HasIsActive) -> None:
    obj.is_active = False
    db.flush()
