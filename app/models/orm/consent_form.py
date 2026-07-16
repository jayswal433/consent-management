from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ConsentForm(Base):
    """Consent form model for DPDP system."""

    __tablename__ = "consent_forms"

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
    name = Column(String(80), nullable=False, index=True)
    code = Column(String(30), nullable=False, unique=True, index=True)
    owner = Column(String(100), nullable=True)
    purpose_short = Column(String(200), nullable=True)
    purpose = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    legal_basis = Column(String(30), nullable=True)
    retention_days = Column(String(10), nullable=False, default="365")
    expiry_days = Column(String(10), nullable=False, default="365")
    third_parties = Column(JSON, nullable=True)
    user_rights = Column(JSON, nullable=True)
    data_fields = Column(JSON, nullable=True)
    status = Column(String(20), default="draft", nullable=False, index=True)
    active_version = Column(String(10), nullable=True)
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

    org = relationship("Org", foreign_keys=[org_id])
    versions = relationship(
        "FormVersion", back_populates="form", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_dpdp_consent_forms_org_id", "org_id"),
        Index("idx_dpdp_consent_forms_code", "code"),
        Index("idx_dpdp_consent_forms_status", "status"),
    )
