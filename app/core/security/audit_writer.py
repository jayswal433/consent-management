from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

logger = logging.getLogger(__name__)


async def write_audit_entry(
    session: AsyncSession,
    actor: str,
    actor_type: str,
    action: str,
    target: str | None = None,
    version: str | None = None,
    details: str | None = None,
    org_id: str | None = None,
) -> "AuditLog":
    """
    Write an immutable audit entry with SHA-256 hash chain.

    Creates a new audit log entry with a SHA-256 hash computed from the
    entry content and the previous entry's hash (hash chain). This ensures
    audit log integrity.

    Args:
        session: AsyncSession for database operations.
        actor: Actor identifier (user_id, admin_id, or "system").
        actor_type: Type of actor (admin, user, or system).
        action: Action name (e.g., "consent_granted").
        target: Optional target identifier (form_id, user_id, etc.).
        version: Optional version string.
        details: Optional additional details as a string.
        org_id: Optional organization ID.

    Returns:
        The newly created AuditLog instance.

    Raises:
        ImportError: If AuditLog model is not available.
    """
    try:
        from app.models.orm.audit_log import AuditLog
    except ImportError as e:
        raise ImportError("AuditLog model must be defined in app.models.orm") from e

    ts = datetime.now(UTC)
    entry_id = str(uuid.uuid4())

    last_entry = await session.scalar(
        select(AuditLog).order_by(AuditLog.ts.desc()).limit(1)
    )
    prev_hash = last_entry.hash if last_entry else ""

    hash_input = (
        f"{entry_id}|{ts.isoformat()}|{actor}|{action}|"
        f"{target or ''}|{details or ''}|{prev_hash}"
    )
    entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    new_entry = AuditLog(
        id=entry_id,
        ts=ts,
        actor=actor,
        actor_type=actor_type,
        action=action,
        target=target,
        version=version,
        details=details,
        prev_hash=prev_hash,
        hash=entry_hash,
        org_id=org_id,
    )

    session.add(new_entry)
    await session.flush()

    return new_entry
