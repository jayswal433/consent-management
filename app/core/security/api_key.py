"""API key validation for public consent endpoints.

Validates organization-issued API keys against the dpdp_org_api_keys table.
Updates last_used_at asynchronously (fire-and-forget).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import AsyncSessionLocal, get_db_session
from app.models.orm.org_api_key import OrgApiKey

logger = logging.getLogger(__name__)


async def require_org_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Validate organization API key and return org/key context.

    Validates the X-API-Key header against the dpdp_org_api_keys table:
    - Hashes the provided key with SHA256
    - Looks up the hash in the database
    - Verifies key is active (is_active="1")
    - Verifies key has not expired
    - Updates last_used_at asynchronously (non-blocking)

    Args:
        x_api_key: API key from X-API-Key header.
        session: Database session (injected via Depends).

    Returns:
        Dictionary with org_id and key_id for downstream routes.

    Raises:
        HTTPException: 401 if key missing, invalid, expired, or revoked.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "MISSING_API_KEY",
                "message": "X-API-Key header is required",
            },
        )

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    try:
        result = await session.execute(
            select(OrgApiKey).where(OrgApiKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()
    except SQLAlchemyError as exc:
        logger.exception("Database error while validating API key")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "DATABASE_UNAVAILABLE",
                "message": "Database is unavailable. Check DB connection settings.",
            },
        ) from exc

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_API_KEY",
                "message": "API key not found or invalid",
            },
        )

    if api_key.is_active != "1":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "REVOKED_API_KEY",
                "message": "API key has been revoked",
            },
        )

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "EXPIRED_API_KEY",
                "message": "API key has expired",
            },
        )

    asyncio.create_task(_update_last_used(api_key.id))

    return {"org_id": api_key.org_id, "key_id": api_key.id}


async def _update_last_used(key_id: str) -> None:
    """Fire-and-forget update of last_used_at timestamp.

    Args:
        key_id: API key ID to update.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(OrgApiKey)
                .where(OrgApiKey.id == key_id)
                .values(last_used_at=datetime.now(UTC))
            )
            await session.commit()
    except Exception:
        pass


async def require_public_api_key(
    api_context: dict[str, str] = Depends(require_org_api_key),
) -> dict[str, str]:
    """Alias for require_org_api_key for backward compatibility.

    Args:
        api_context: Organization context from require_org_api_key.

    Returns:
        Organization context (org_id and key_id).
    """
    return api_context
