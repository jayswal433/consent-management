from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, Text

from app.db.base import Base


class AuditLog(Base):
    """Immutable audit log model with hash chain verification."""

    __tablename__ = "audit_log"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    ts = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    actor = Column(String(100), nullable=False, index=True)
    actor_type = Column(String(20), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    target = Column(String(100), nullable=True, index=True)
    version = Column(String(10), nullable=True)
    details = Column(Text, nullable=True)
    prev_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=False)
    org_id = Column(String(36), nullable=True, index=True)

    __table_args__ = (
        Index("idx_dpdp_audit_log_ts", "ts"),
        Index("idx_dpdp_audit_log_action", "action"),
        Index("idx_dpdp_audit_log_actor", "actor"),
        Index("idx_dpdp_audit_log_org_id", "org_id"),
    )
