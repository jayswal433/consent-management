from __future__ import annotations

import re

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.form_version import FormVersion
from app.repositories.base import BaseRepository


class VersionRepository(BaseRepository[FormVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FormVersion, session)

    async def get_by_form_and_version(
        self, form_id: str, version: str
    ) -> FormVersion | None:
        result = await self.session.execute(
            select(FormVersion).where(
                and_(FormVersion.form_id == form_id, FormVersion.version == version)
            )
        )
        return result.scalar_one_or_none()

    async def get_active_version(self, form_id: str) -> FormVersion | None:
        result = await self.session.execute(
            select(FormVersion).where(
                and_(
                    FormVersion.form_id == form_id,
                    FormVersion.status == "active",
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_draft_version(self, form_id: str) -> FormVersion | None:
        result = await self.session.execute(
            select(FormVersion).where(
                and_(
                    FormVersion.form_id == form_id,
                    FormVersion.status == "draft",
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_in_review_version(self, form_id: str) -> FormVersion | None:
        result = await self.session.execute(
            select(FormVersion).where(
                and_(
                    FormVersion.form_id == form_id,
                    FormVersion.status == "in_review",
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(self, form_id: str) -> list[FormVersion]:
        result = await self.session.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id)
            .order_by(FormVersion.created_at.desc())
        )
        return result.scalars().all()

    async def get_next_version_string(self, form_id: str) -> str:
        result = await self.session.execute(
            select(FormVersion)
            .where(FormVersion.form_id == form_id)
            .order_by(FormVersion.created_at.desc())
        )
        versions = result.scalars().all()

        if not versions:
            return "v1.0"

        version_numbers = []
        for v in versions:
            match = re.match(r"v(\d+)\.(\d+)", v.version)
            if match:
                major = int(match.group(1))
                version_numbers.append(major)

        if not version_numbers:
            return "v1.0"

        next_major = max(version_numbers) + 1
        return f"v{next_major}.0"
