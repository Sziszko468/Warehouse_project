from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.user import User


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    STATUS_CHANGE = "status_change"
    SOFT_DELETE = "soft_delete"


class AuditLog(Base):
    """Generic write-audit trail across master data and orders/shipments. Never updated or
    deleted. Covers writes only (create/update/status-change/soft-delete), not reads."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity_type", "entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[int] = mapped_column(index=True, nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(
            AuditAction, native_enum=False, validate_strings=True, values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
    )
    performed_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    performed_by: Mapped[User] = relationship()
