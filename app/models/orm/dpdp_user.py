from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class DpdpUser(Base):
    """User model for DPDP system."""

    __tablename__ = "users"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    org_id = Column(
        String(36),
        ForeignKey("orgs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role = Column(String(30), nullable=False, index=True)
    name = Column(Text, nullable=False)
    name_hash = Column(String(64), nullable=False, index=True)
    email = Column(Text, nullable=False)
    email_hash = Column(String(64), nullable=False, unique=True, index=True)
    phone = Column(Text, nullable=True)
    phone_hash = Column(String(64), nullable=True, index=True)
    initials = Column(Text, nullable=True)
    password_hash = Column(String(255), nullable=False)
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

    # lazy="raise" surfaces accidental lazy loads immediately instead of
    # raising a cryptic MissingGreenlet error under async SQLAlchemy. Load
    # this relationship explicitly via selectinload/joinedload when needed.
    org = relationship("Org", foreign_keys=[org_id], lazy="raise")
