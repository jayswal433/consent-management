from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_user import DpdpUser
from app.repositories.base import BaseRepository


class DpdpUserRepository(BaseRepository[DpdpUser]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DpdpUser, session)

    async def get_by_email_hash(self, email_hash: str) -> Optional[DpdpUser]:
        return await self.get_by_field("email_hash", email_hash)

    async def get_by_id_with_consents(
        self, user_id: str, session: AsyncSession
    ) -> tuple[Optional[DpdpUser], list[DpdpConsent]]:
        user = await self.get_by_id(user_id)
        if not user:
            return None, []

        consents_result = await session.execute(
            select(DpdpConsent).where(DpdpConsent.user_id == user_id)
        )
        consents = consents_result.scalars().all()

        return user, consents

    async def list_users(
        self, org_id: str | None, page: int, limit: int
    ) -> tuple[list[DpdpUser], int]:
        offset = (page - 1) * limit

        query = select(self.model).where(self.model.is_active == "1")
        if org_id:
            query = query.where(self.model.org_id == org_id)

        query = (
            query.order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        users = result.scalars().all()

        count_query = select(func.count()).select_from(self.model)
        if org_id:
            count_query = count_query.where(self.model.org_id == org_id)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return users, total

    async def count_all(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
