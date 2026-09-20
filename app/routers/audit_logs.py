from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import audit_log as crud_audit_log
from app.database import get_db
from app.dependencies import PaginationParams, require_admin
from app.messages import Messages
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User
from app.routers.helpers import get_or_404
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import Page

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=Page[AuditLogRead])
def list_audit_logs(
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: AuditAction | None = None,
    performed_by_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Page[AuditLogRead]:
    items, total = crud_audit_log.list_audit_logs(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by_id=performed_by_id,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{audit_log_id}", response_model=AuditLogRead)
def get_audit_log(audit_log_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> AuditLog:
    return get_or_404(crud_audit_log.get, db, audit_log_id, Messages.AUDIT_LOG_NOT_FOUND)
