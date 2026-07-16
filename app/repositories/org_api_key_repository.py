"""Repository for OrgApiKey model operations."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.org_api_key import OrgApiKey
from app.repositories.base import BaseRepository


class OrgApiKeyRepository(BaseRepository[OrgApiKey]):
    """Repository for managing organization API keys."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OrgApiKey, session)

    async def get_by_org_id(self, org_id: str) -> list[OrgApiKey]:
        """Get all API keys for an organization.

        Args:
            org_id: Organization ID.

        Returns:
            List of API keys.
        """
        result = await self.session.execute(
            select(self.model).where(self.model.org_id == org_id)
        )
        return result.scalars().all()

    async def get_by_key_hash(self, key_hash: str) -> Optional[OrgApiKey]:
        """Get API key by its SHA256 hash.

        Args:
            key_hash: SHA256 hash of the API key.

        Returns:
            API key if found, None otherwise.
        """
        return await self.get_by_field("key_hash", key_hash)

    async def get_by_key_prefix(self, key_prefix: str) -> Optional[OrgApiKey]:
        """Get API key by its prefix.

        Args:
            key_prefix: First 16 chars of the API key.

        Returns:
            API key if found, None otherwise.
        """
        return await self.get_by_field("key_prefix", key_prefix)
