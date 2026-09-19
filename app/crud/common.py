from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def paginate(db: Session, stmt: Select, *, limit: int, offset: int) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.limit(limit).offset(offset)).all()
    return list(items), total
