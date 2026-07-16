from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for audit log operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def get_last_entry(
        self, org_id: str | None = None
    ) -> AuditLog | None:
        """
        Get the most recent audit entry for hash chain verification.

        Args:
            org_id: Optional organization ID filter

        Returns:
            The most recent AuditLog entry or None
        """
        filters = []
        if org_id:
            filters.append(AuditLog.org_id == org_id)

        stmt = select(AuditLog)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(desc(AuditLog.ts)).limit(1)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_audit(
        self,
        actor_type: str | None = None,
        action: str | None = None,
        form_id: str | None = None,
        user_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AuditLog], int]:
        """
        List audit entries with filters and pagination.

        Args:
            actor_type: Filter by actor type
            action: Filter by action
            form_id: Filter by target form
            user_id: Filter by target user
            from_date: Filter from date
            to_date: Filter to date
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Tuple of (audit entries list, total count)
        """
        filters = []

        if actor_type:
            filters.append(AuditLog.actor_type == actor_type)
        if action:
            filters.append(AuditLog.action == action)
        if form_id:
            filters.append(AuditLog.target == form_id)
        if user_id:
            filters.append(AuditLog.actor == user_id)
        if from_date:
            filters.append(AuditLog.ts >= from_date)
        if to_date:
            filters.append(AuditLog.ts <= to_date)

        stmt = select(AuditLog)
        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(AuditLog)
        if filters:
            count_stmt = count_stmt.where(and_(*filters))

        total = await self.session.scalar(count_stmt)

        stmt = stmt.order_by(desc(AuditLog.ts))
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        entries = result.scalars().all()

        return entries, total or 0
