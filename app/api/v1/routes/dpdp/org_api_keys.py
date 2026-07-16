"""Routes for organization API key management."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, require_permission
from app.schemas.dpdp.org_api_key import CreateApiKeyRequest
from app.services.dpdp.org_api_key_service import OrgApiKeyService

router = APIRouter(
    prefix="/orgs",
    tags=["Organization API Keys"],
)


@router.post("/{org_id}-keys", status_code=201)
async def create_api_key(
    org_id: str,
    data: CreateApiKeyRequest,
    token_data: Annotated[
        dict, Depends(require_permission(Permission.UPDATE_ORG_SETTINGS))
    ],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Create a new API key for an organization.

    The raw key is returned only once - store it securely on the client side.
    The key can be used in X-API-Key header for public consent endpoints.

    Args:
        org_id: Organization ID.
        data: API key creation request (label, optional expires_at).
        token_data: JWT token data with actor ID.
        session: Database session.

    Returns:
        Created API key with raw_key shown once.
    """
    actor_id = token_data.get("sub")
    service = OrgApiKeyService(session)
    return await service.create_api_key(org_id, data, actor_id)


@router.get("/{org_id}-keys")
async def list_api_keys(
    org_id: str,
    token_data: Annotated[
        dict, Depends(require_permission(Permission.UPDATE_ORG_SETTINGS))
    ],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List all API keys for an organization.

    Args:
        org_id: Organization ID.
        token_data: JWT token data.
        session: Database session.

    Returns:
        List of API keys (raw key never included).
    """
    service = OrgApiKeyService(session)
    return await service.list_api_keys(org_id)


@router.delete("/{org_id}-keys/{key_id}", status_code=200)
async def revoke_api_key(
    org_id: str,
    key_id: str,
    token_data: Annotated[
        dict, Depends(require_permission(Permission.UPDATE_ORG_SETTINGS))
    ],
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Revoke (deactivate) an API key.

    Args:
        org_id: Organization ID.
        key_id: API key ID to revoke.
        token_data: JWT token data with actor ID.
        session: Database session.

    Returns:
        Revoked API key details.
    """
    actor_id = token_data.get("sub")
    service = OrgApiKeyService(session)
    return await service.revoke_api_key(key_id, org_id, actor_id)
