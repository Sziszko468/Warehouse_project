from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.models.audit_log import AuditAction, AuditLog


def paginate(db: Session, stmt: Select, *, limit: int, offset: int) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.limit(limit).offset(offset)).all()
    return list(items), total


def _record(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    performed_by_id: int,
    changes: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by_id=performed_by_id,
            changes=changes,
        )
    )
    db.flush()


def create[ModelT](db: Session, model_cls: type[ModelT], payload: BaseModel, *, performed_by_id: int) -> ModelT:
    obj = model_cls(**payload.model_dump())
    db.add(obj)
    db.flush()
    db.refresh(obj)
    _record(
        db,
        entity_type=model_cls.__name__,
        entity_id=obj.id,
        action=AuditAction.CREATE,
        performed_by_id=performed_by_id,
    )
    return obj


def update[ModelT](db: Session, obj: ModelT, payload: BaseModel, *, performed_by_id: int) -> ModelT:
    changes: dict[str, dict[str, Any]] = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        old_value = getattr(obj, field)
        if old_value != value:
            changes[field] = {"old": str(old_value), "new": str(value)}
        setattr(obj, field, value)
    db.flush()
    db.refresh(obj)
    if changes:
        _record(
            db,
            entity_type=type(obj).__name__,
            entity_id=obj.id,
            action=AuditAction.UPDATE,
            performed_by_id=performed_by_id,
            changes=changes,
        )
    return obj


class _HasIsActive(Protocol):
    is_active: bool


def soft_delete(db: Session, obj: _HasIsActive, *, performed_by_id: int) -> None:
    obj.is_active = False
    db.flush()
    _record(
        db,
        entity_type=type(obj).__name__,
        entity_id=obj.id,  # type: ignore[attr-defined]
        action=AuditAction.SOFT_DELETE,
        performed_by_id=performed_by_id,
    )
