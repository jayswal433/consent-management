from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class DpdpConsent(Base):
    """Consent record model for DPDP system."""

    __tablename__ = "consents"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    form_id = Column(
        String(36),
        ForeignKey("consent_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(String(10), nullable=False)
    status = Column(String(20), default="granted", nullable=False, index=True)
    optional_fields = Column(Text, nullable=True)
    ip_hash = Column(String(64), nullable=True)
    user_agent_hash = Column(String(64), nullable=True)
    channel = Column(String(20), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    receipt_token = Column(String(512), nullable=True)
    withdrawal_receipt_id = Column(String(36), nullable=True)
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

    user = relationship("DpdpUser", foreign_keys=[user_id])
    form = relationship("ConsentForm", foreign_keys=[form_id])

    __table_args__ = (
        UniqueConstraint(
            "user_id", "form_id", "version", name="uq_user_form_version"
        ),
        Index("idx_dpdp_consents_user_id", "user_id"),
        Index("idx_dpdp_consents_form_id", "form_id"),
        Index("idx_dpdp_consents_status", "status"),
        Index("idx_dpdp_consents_expires_at", "expires_at"),
    )
