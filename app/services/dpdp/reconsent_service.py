from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.audit_writer import write_audit_entry
from app.models.orm.async_job import AsyncJob
from app.models.orm.consent_form import ConsentForm
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import AuditAction, ConsentStatus, JobStatus
from app.repositories.dpdp_consent_repository import DpdpConsentRepository
from app.schemas.dpdp.reconsent import (
    BulkRevokeResponse,
    JobStatusResponse,
    ReconsentNotifyResponse,
    ReconsentPendingResponse,
)


class ReconsentService:
    """Service for managing reconsent operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DpdpConsentRepository(session)

    async def get_pending_reconsent(
        self, form_id: str | None, page: int, limit: int
    ) -> dict[str, Any]:
        """
        Get users with pending reconsent requirements.

        Args:
            form_id: Filter by form ID.
            page: Page number (1-indexed).
            limit: Items per page.

        Returns:
            List of pending reconsent items.

        Raises:
            ValueError: If form_id is None.
        """
        if not form_id:
            raise ValueError("FORM_ID_REQUIRED")

        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == form_id)
        )
        if not form:
            raise ValueError("FORM_NOT_FOUND")

        active_version = form.active_version
        if not active_version:
            raise ValueError("NO_ACTIVE_VERSION")

        pending, total = await self.repo.get_pending_reconsent(
            form_id=form_id,
            active_version=active_version,
            page=page,
            limit=limit,
        )

        items = [
            {
                "user_id": p.user_id,
                "form_id": p.form_id,
                "current_version": p.version,
                "required_version": active_version,
            }
            for p in pending
        ]

        response = ReconsentPendingResponse(
            items=items, total=total, page=page, limit=limit
        )
        return response.model_dump()

    async def notify_users(
        self, form_id: str, version: str, user_ids: list[str] | None, actor_id: str
    ) -> dict[str, Any]:
        """
        Notify users about reconsent requirement.

        Args:
            form_id: Form ID.
            version: Required version.
            user_ids: List of user IDs or None for all pending.
            actor_id: ID of the actor triggering notification.

        Returns:
            Job details with notified count.

        Raises:
            ValueError: If form not found.
        """
        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == form_id)
        )
        if not form:
            raise ValueError("FORM_NOT_FOUND")

        if user_ids is None or len(user_ids) == 0:
            pending, total = await self.repo.get_pending_reconsent(
                form_id=form_id,
                active_version=form.active_version or version,
                page=1,
                limit=100000,
            )
            user_ids = [p.user_id for p in pending]
        else:
            total = len(user_ids)

        job_id = str(uuid.uuid4())
        job = AsyncJob(
            id=job_id,
            job_type="reconsent_notify",
            status=JobStatus.RUNNING.value,
            form_id=form_id,
            initiated_by=actor_id,
            total=str(total),
            processed="0",
            failed="0",
        )

        self.session.add(job)
        await self.session.flush()

        for user_id in user_ids:
            await write_audit_entry(
                self.session,
                actor=actor_id,
                actor_type="admin",
                action=AuditAction.RECONSENT_NOTIFIED.value,
                target=user_id,
                version=version,
                details=f"form_id={form_id}, job_id={job_id}",
            )

        now = datetime.now(UTC)
        await self.session.execute(
            AsyncJob.__table__.update()
            .where(AsyncJob.id == job_id)
            .values(
                status=JobStatus.COMPLETED.value,
                processed=str(total),
                completed_at=now,
            )
        )
        await self.session.flush()

        response = ReconsentNotifyResponse(
            notified=len(user_ids),
            job_id=job_id,
        )
        return response.model_dump()

    async def bulk_revoke(
        self,
        form_id: str,
        older_than: datetime,
        dry_run: bool,
        actor_id: str,
    ) -> dict[str, Any]:
        """
        Bulk revoke consents for stale versions.

        Args:
            form_id: Form ID.
            older_than: ISO datetime; revoke consents older than this.
            dry_run: If True, don't modify database.
            actor_id: ID of the actor revoking.

        Returns:
            Revoke operation results.

        Raises:
            ValueError: If form not found.
        """
        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == form_id)
        )
        if not form:
            raise ValueError("FORM_NOT_FOUND")

        active_version = form.active_version
        if not active_version:
            raise ValueError("NO_ACTIVE_VERSION")

        stale_consents = await self.repo.get_stale_consents_for_revoke(
            form_id=form_id,
            active_version=active_version,
            older_than=older_than,
        )

        affected_users = list(set(c.user_id for c in stale_consents))
        revoke_count = len(stale_consents)

        if not dry_run:
            now = datetime.now(UTC)
            for consent in stale_consents:
                await self.repo.update_by_id(
                    consent.id,
                    status=ConsentStatus.EXPIRED.value,
                )

                await write_audit_entry(
                    self.session,
                    actor=actor_id,
                    actor_type="system",
                    action=AuditAction.AUTO_REVOKED.value,
                    target=consent.user_id,
                    version=consent.version,
                    details=f"form_id={form_id}, older_than={older_than.isoformat()}",
                )

        response = BulkRevokeResponse(
            revoked=revoke_count,
            dry_run=dry_run,
            affected_users=affected_users,
        )
        return response.model_dump()

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get async job status.

        Args:
            job_id: Job ID.

        Returns:
            Job status details.

        Raises:
            ValueError: If job not found.
        """
        job = await self.session.scalar(
            select(AsyncJob).where(AsyncJob.id == job_id)
        )
        if not job:
            raise ValueError("JOB_NOT_FOUND")

        response = JobStatusResponse(
            job_id=job.id,
            status=job.status,
            notified=int(job.processed),
            failed=int(job.failed),
            completed_at=job.completed_at,
        )
        return response.model_dump()
