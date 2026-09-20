from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.audit_log import AuditAction
from app.schemas.common import UserBrief


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    action: AuditAction
    performed_by: UserBrief
    summary: str | None
    changes: dict | None
    created_at: datetime
