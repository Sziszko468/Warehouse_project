from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.crud.common import paginate
from app.models.audit_log import AuditAction, AuditLog


def get(db: Session, audit_log_id: int) -> AuditLog | None:
    stmt = select(AuditLog).where(AuditLog.id == audit_log_id).options(joinedload(AuditLog.performed_by))
    return db.scalar(stmt)


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: AuditAction | None = None,
    performed_by_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    stmt = (
        select(AuditLog)
        .options(joinedload(AuditLog.performed_by))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if performed_by_id is not None:
        stmt = stmt.where(AuditLog.performed_by_id == performed_by_id)
    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return paginate(db, stmt, limit=limit, offset=offset)
