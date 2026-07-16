"""Organization API Key model for DPDP system.

Stores API keys for organizations to access public consent endpoints.
Each key is hashed with SHA256 and identified by a prefix.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String

from app.db.base import Base


class OrgApiKey(Base):
    """Organization API Key model."""

    __tablename__ = "org_api_keys"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    org_id = Column(
        String(36),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label = Column(String(100), nullable=False)
    key_prefix = Column(String(16), unique=True, nullable=False, index=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(String(1), default="1", nullable=False, index=True)
    created_by = Column(String(36), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_dpdp_org_api_keys_org_id", "org_id"),
        Index("idx_dpdp_org_api_keys_is_active", "is_active"),
    )
