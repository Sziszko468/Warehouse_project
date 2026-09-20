"""add audit log

Revision ID: d27733682259
Revises: 3a0511e8becc
Create Date: 2026-09-20

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d27733682259"
down_revision: str | None = "3a0511e8becc"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(13), nullable=False),
        sa.Column("performed_by_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["performed_by_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_performed_by_id", "audit_logs", ["performed_by_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
