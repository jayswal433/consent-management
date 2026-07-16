from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class FormVersion(Base):
    """Form version model for DPDP system."""

    __tablename__ = "form_versions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    form_id = Column(
        String(36),
        ForeignKey("consent_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(String(10), nullable=False)
    status = Column(String(20), default="draft", nullable=False, index=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    purpose = Column(Text, nullable=False)
    legal_basis = Column(String(30), nullable=False)
    retention_days = Column(String(10), nullable=False, default="365")
    expiry_days = Column(String(10), nullable=False, default="365")
    third_parties = Column(JSON, nullable=True)
    user_rights = Column(JSON, nullable=True)
    data_fields = Column(JSON, nullable=True)
    custom_body = Column(Text, nullable=True)
    reviewer_note = Column(Text, nullable=True)
    reviewer_sign_off = Column(String(36), nullable=True)
    review_note = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(String(36), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
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

    form = relationship("ConsentForm", back_populates="versions", foreign_keys=[form_id])

    __table_args__ = (
        UniqueConstraint("form_id", "version", name="uq_form_id_version"),
        Index("idx_dpdp_form_versions_form_id", "form_id"),
        Index("idx_dpdp_form_versions_status", "status"),
    )
