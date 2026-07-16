"""Service for managing organization API keys."""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.core.security.audit_writer import write_audit_entry
from app.models.orm.dpdp_enums import ActorType, AuditAction
from app.repositories.org_api_key_repository import OrgApiKeyRepository
from app.schemas.dpdp.org_api_key import (
    ApiKeyCreateResponse,
    ApiKeyListItem,
    CreateApiKeyRequest,
)


class OrgApiKeyService:
    """Service for managing organization API keys."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrgApiKeyRepository(session)

    async def create_api_key(
        self, org_id: str, data: CreateApiKeyRequest, actor_id: str
    ) -> dict[str, Any]:
        """Create a new API key for an organization.

        Generates a 32-byte random key with format: csk_<hex_string>
        Returns the raw key ONCE in response - it is never logged or stored.

        Args:
            org_id: Organization ID.
            data: Create request with label and optional expires_at.
            actor_id: ID of the actor creating the key.

        Returns:
            Dictionary with newly created key details (including raw_key).
        """
        raw_key_bytes = secrets.token_bytes(32)
        raw_key_hex = raw_key_bytes.hex()
        raw_key = f"csk_{raw_key_hex}"
        key_prefix = raw_key[:16]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = await self.repo.create(
            org_id=org_id,
            label=data.label,
            key_prefix=key_prefix,
            key_hash=key_hash,
            is_active="1",
            created_by=actor_id,
            created_at=datetime.now(UTC),
            expires_at=data.expires_at,
        )

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.API_KEY_CREATED.value,
            target=api_key.id,
            org_id=org_id,
            details=f"API key created: {data.label}",
        )

        response = ApiKeyCreateResponse(
            id=api_key.id,
            label=api_key.label,
            key_prefix=api_key.key_prefix,
            raw_key=raw_key,
            org_id=api_key.org_id,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
        )

        return StandardResponse.created(
            data=response.model_dump(),
            message="API key created successfully",
        ).make

    async def list_api_keys(self, org_id: str) -> dict[str, Any]:
        """List all API keys for an organization.

        Args:
            org_id: Organization ID.

        Returns:
            List of API keys (raw key never included).
        """
        api_keys = await self.repo.get_by_org_id(org_id)

        items = [
            ApiKeyListItem(
                id=key.id,
                label=key.label,
                key_prefix=key.key_prefix,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at,
            )
            for key in api_keys
        ]

        return StandardResponse.success(
            data={"items": [item.model_dump() for item in items]},
            message="API keys retrieved successfully",
        ).make

    async def revoke_api_key(
        self, key_id: str, org_id: str, actor_id: str
    ) -> dict[str, Any]:
        """Revoke (deactivate) an API key.

        Args:
            key_id: API key ID.
            org_id: Organization ID (for ownership verification).
            actor_id: ID of the actor revoking the key.

        Returns:
            Standard response with updated key status.

        Raises:
            ValueError: If key not found or doesn't belong to org.
        """
        api_key = await self.repo.get_by_id(key_id)
        if not api_key:
            return StandardResponse.not_found(
                message="API key not found",
                data={"error": "KEY_NOT_FOUND"},
            ).make

        if api_key.org_id != org_id:
            return StandardResponse.bad_request(
                message="API key does not belong to this organization",
                data={"error": "ORG_MISMATCH"},
            ).make

        updated_key = await self.repo.update_by_id(key_id, is_active="0")

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.API_KEY_REVOKED.value,
            target=key_id,
            org_id=org_id,
            details=f"API key revoked: {updated_key.label}",
        )

        return StandardResponse.success(
            data={
                "id": updated_key.id,
                "label": updated_key.label,
                "is_active": updated_key.is_active,
            },
            message="API key revoked successfully",
        ).make
