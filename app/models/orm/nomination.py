from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text

from app.db.base import Base


class Nomination(Base):
    """Nominee registration model for DPDP system."""

    __tablename__ = "nominations"

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
    nominee_name = Column(Text, nullable=False)
    nominee_email = Column(Text, nullable=False)
    nominee_email_hash = Column(String(64), nullable=False, index=True)
    nominee_phone = Column(Text, nullable=True)
    nominee_phone_hash = Column(String(64), nullable=True, index=True)
    is_active = Column(String(1), default="1", nullable=False, index=True)
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
        Index("idx_dpdp_nominations_user_id", "user_id"),
        Index("idx_dpdp_nominations_email_hash", "nominee_email_hash"),
    )
