from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.async_job import AsyncJob
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[AsyncJob]):
    """Repository for async job operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AsyncJob, session)

    async def list_jobs_for_form(self, form_id: str) -> list[AsyncJob]:
        """
        Get all jobs for a given form.

        Args:
            form_id: The form ID

        Returns:
            List of AsyncJob instances
        """
        stmt = (
            select(AsyncJob)
            .where(AsyncJob.form_id == form_id)
            .order_by(AsyncJob.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_job(
        self,
        job_type: str,
        org_id: str | None,
        form_id: str | None,
        initiated_by: str,
    ) -> AsyncJob:
        """
        Create a new async job.

        Args:
            job_type: Type of job (audit_export, notification, etc.)
            org_id: Optional organization ID
            form_id: Optional form ID
            initiated_by: User ID who initiated the job

        Returns:
            Created AsyncJob instance
        """
        return await self.create(
            job_type=job_type,
            status="pending",
            org_id=org_id,
            form_id=form_id,
            initiated_by=initiated_by,
            total="0",
            processed="0",
            failed="0",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
