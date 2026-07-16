from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Index, String, Text

from app.db.base import Base


class AsyncJob(Base):
    """Async job tracking model for DPDP system."""

    __tablename__ = "async_jobs"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    job_type = Column(String(30), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    org_id = Column(String(36), nullable=True, index=True)
    form_id = Column(String(36), nullable=True, index=True)
    initiated_by = Column(String(36), nullable=True)
    total = Column(String(10), default="0", nullable=False)
    processed = Column(String(10), default="0", nullable=False)
    failed = Column(String(10), default="0", nullable=False)
    result_url = Column(Text, nullable=True)
    result_url_expires_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
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
        Index("idx_dpdp_async_jobs_type", "job_type"),
        Index("idx_dpdp_async_jobs_status", "status"),
        Index("idx_dpdp_async_jobs_org_id", "org_id"),
    )
