from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.org import Org
from app.repositories.base import BaseRepository


class OrgRepository(BaseRepository[Org]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Org, session)

    async def get_by_name(self, name: str) -> Optional[Org]:
        return await self.get_by_field("name", name)

    async def get_by_short_code(self, code: str) -> Optional[Org]:
        return await self.get_by_field("short_code", code)

    async def list_orgs(
        self, page: int, limit: int
    ) -> tuple[list[Org], int]:
        offset = (page - 1) * limit
        result = await self.session.execute(
            select(self.model)
            .where(self.model.status == "active")
            .order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        orgs = result.scalars().all()

        count_result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        total = count_result.scalar_one()

        return orgs, total

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
