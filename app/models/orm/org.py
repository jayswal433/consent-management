from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text, Index
from sqlalchemy.sql import func

from app.db.base import Base


class Org(Base):
    """Organization model for DPDP system."""

    __tablename__ = "orgs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    name = Column(String(120), unique=True, nullable=False, index=True)
    short_code = Column(String(20), unique=True, nullable=True, index=True)
    color = Column(String(7), nullable=True)
    role = Column(String(50), nullable=True)
    plan = Column(String(30), default="free", nullable=False)
    dpo_name = Column(Text, nullable=True)
    dpo_email = Column(Text, nullable=True)
    dpo_email_hash = Column(
        String(64), nullable=True, index=True, unique=False
    )
    dpdp_reg_id = Column(String(50), nullable=True, index=True)
    webhook_url = Column(String(500), nullable=True)
    status = Column(String(20), default="active", nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_dpdp_orgs_name", "name"),
        Index("idx_dpdp_orgs_status", "status"),
    )
