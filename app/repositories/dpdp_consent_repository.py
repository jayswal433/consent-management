from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import ConsentStatus
from app.repositories.base import BaseRepository


class DpdpConsentRepository(BaseRepository[DpdpConsent]):
    """Repository for DpdpConsent ORM model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DpdpConsent, session)

    async def get_active_consent(
        self, user_id: str, form_id: str
    ) -> DpdpConsent | None:
        """Get most recent granted consent for user + form."""
        result = await self.session.execute(
            select(DpdpConsent)
            .where(
                and_(
                    DpdpConsent.user_id == user_id,
                    DpdpConsent.form_id == form_id,
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                )
            )
            .order_by(desc(DpdpConsent.granted_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_user_form_version(
        self, user_id: str, form_id: str, version: str
    ) -> DpdpConsent | None:
        """Get consent by user, form, and version."""
        result = await self.session.execute(
            select(DpdpConsent).where(
                and_(
                    DpdpConsent.user_id == user_id,
                    DpdpConsent.form_id == form_id,
                    DpdpConsent.version == version,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_consents(
        self,
        user_id: str | None,
        form_id: str | None,
        version: str | None,
        status: str | None,
        from_date: datetime | None,
        to_date: datetime | None,
        page: int,
        limit: int,
    ) -> tuple[list[DpdpConsent], int]:
        """List consents with filters and pagination."""
        conditions = []

        if user_id:
            conditions.append(DpdpConsent.user_id == user_id)
        if form_id:
            conditions.append(DpdpConsent.form_id == form_id)
        if version:
            conditions.append(DpdpConsent.version == version)
        if status:
            conditions.append(DpdpConsent.status == status)
        if from_date:
            conditions.append(DpdpConsent.granted_at >= from_date)
        if to_date:
            conditions.append(DpdpConsent.granted_at <= to_date)

        where_clause = and_(*conditions) if conditions else None

        count_result = await self.session.execute(
            select(func.count()).select_from(DpdpConsent).where(where_clause)
        )
        total = count_result.scalar_one()

        offset = (page - 1) * limit
        query = select(DpdpConsent).order_by(desc(DpdpConsent.created_at))
        if where_clause is not None:
            query = query.where(where_clause)
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def get_pending_reconsent(
        self, form_id: str, active_version: str, page: int, limit: int
    ) -> tuple[list[DpdpConsent], int]:
        """Get consents requiring reconsent (version != active and granted)."""
        conditions = [
            DpdpConsent.form_id == form_id,
            DpdpConsent.version != active_version,
            DpdpConsent.status == ConsentStatus.GRANTED.value,
        ]

        count_result = await self.session.execute(
            select(func.count())
            .select_from(DpdpConsent)
            .where(and_(*conditions))
        )
        total = count_result.scalar_one()

        offset = (page - 1) * limit
        query = (
            select(DpdpConsent)
            .where(and_(*conditions))
            .order_by(desc(DpdpConsent.created_at))
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        items = result.scalars().all()

        return items, total

    async def count_active_for_form(self, form_id: str) -> int:
        """Count active (granted) consents for a form."""
        result = await self.session.execute(
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                and_(
                    DpdpConsent.form_id == form_id,
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                )
            )
        )
        return result.scalar_one()

    async def get_stale_consents_for_revoke(
        self, form_id: str, active_version: str, older_than: datetime
    ) -> list[DpdpConsent]:
        """Get consents eligible for auto-revoke (old, non-current version)."""
        result = await self.session.execute(
            select(DpdpConsent).where(
                and_(
                    DpdpConsent.form_id == form_id,
                    DpdpConsent.version != active_version,
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                    DpdpConsent.granted_at < older_than,
                )
            )
        )
        return result.scalars().all()

    async def get_all_user_consents(self, user_id: str) -> list[DpdpConsent]:
        """Get all consents for a user."""
        result = await self.session.execute(
            select(DpdpConsent)
            .where(DpdpConsent.user_id == user_id)
            .order_by(desc(DpdpConsent.created_at))
        )
        return result.scalars().all()
