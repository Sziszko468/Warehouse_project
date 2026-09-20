from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog


def record(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: AuditAction,
    performed_by_id: int,
    summary: str | None = None,
    changes: dict | None = None,
) -> None:
    """Explicit audit entry point for service-layer status transitions (submit/receive/cancel/
    confirm/dispatch/deliver) - these aren't a single-payload field diff the way
    crud.common.update's automatic hook handles master data, so they go through here instead."""
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by_id=performed_by_id,
            summary=summary,
        )
    )
    db.flush()
