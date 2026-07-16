from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.core.security.audit_writer import write_audit_entry
from app.models.orm.dpdp_enums import ActorType, AuditAction
from app.repositories.audit_repository import AuditRepository
from app.repositories.job_repository import JobRepository
from app.schemas.dpdp.audit import (
    AuditExportJobResponse,
    AuditExportRequest,
    AuditExportResponse,
    AuditLogDetailItem,
    AuditLogItem,
    AuditLogListResponse,
)


class AuditService:
    """Service for audit log operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.job_repo = JobRepository(session)

    async def list_audit(
        self,
        actor_type: str | None = None,
        action: str | None = None,
        form_id: str | None = None,
        user_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        List audit entries with filters and pagination.

        Args:
            actor_type: Filter by actor type
            action: Filter by action
            form_id: Filter by form ID
            user_id: Filter by user ID
            from_date: ISO datetime string for filter start
            to_date: ISO datetime string for filter end
            page: Page number (1-indexed)
            limit: Items per page

        Returns:
            Standard response with paginated audit logs
        """
        from_dt = None
        to_dt = None

        try:
            if from_date:
                from_dt = datetime.fromisoformat(from_date)
            if to_date:
                to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            return StandardResponse.bad_request(
                message="Invalid date format. Use ISO datetime.",
                data={"error": "INVALID_DATE_FORMAT"},
            ).make

        entries, total = await self.audit_repo.list_audit(
            actor_type=actor_type,
            action=action,
            form_id=form_id,
            user_id=user_id,
            from_date=from_dt,
            to_date=to_dt,
            page=page,
            limit=limit,
        )

        items = [
            AuditLogItem(
                id=entry.id,
                ts=entry.ts,
                actor=entry.actor,
                actor_type=entry.actor_type,
                action=entry.action,
                target=entry.target,
                version=entry.version,
                details=entry.details,
                hash=entry.hash,
                org_id=entry.org_id,
            )
            for entry in entries
        ]

        response = AuditLogListResponse(
            items=items, total=total, page=page, limit=limit
        )

        return StandardResponse.success(
            data=response.model_dump(),
            message="Audit logs retrieved successfully",
        ).make

    async def get_audit_entry(self, audit_id: str) -> dict[str, Any]:
        """
        Get a single audit entry with prev_hash for verification.

        Args:
            audit_id: The audit log ID

        Returns:
            Standard response with audit entry details
        """
        entry = await self.audit_repo.get_by_id(audit_id)
        if not entry:
            return StandardResponse.not_found(
                message="Audit entry not found",
                data={"error": "AUDIT_NOT_FOUND"},
            ).make

        detail = AuditLogDetailItem(
            id=entry.id,
            ts=entry.ts,
            actor=entry.actor,
            actor_type=entry.actor_type,
            action=entry.action,
            target=entry.target,
            version=entry.version,
            details=entry.details,
            hash=entry.hash,
            prev_hash=entry.prev_hash,
            org_id=entry.org_id,
        )

        return StandardResponse.success(
            data=detail.model_dump(),
            message="Audit entry retrieved successfully",
        ).make

    async def start_export(
        self, data: AuditExportRequest, actor_id: str
    ) -> dict[str, Any]:
        """
        Start an async audit export job.

        Args:
            data: Export request parameters
            actor_id: ID of user initiating export

        Returns:
            Standard response with job ID and download URL
        """
        if data.format not in ("csv", "jsonl"):
            return StandardResponse.bad_request(
                message="Invalid format. Must be csv or jsonl.",
                data={"error": "INVALID_FORMAT"},
            ).make

        job = await self.job_repo.create_job(
            job_type="audit_export",
            org_id=None,
            form_id=data.form_id,
            initiated_by=actor_id,
        )

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.EXPORT_REQUESTED.value,
            target=data.form_id,
            version=data.format,
            org_id=None,
        )

        await self.session.commit()

        response = AuditExportResponse(
            job_id=job.id,
            download_url=f"/v1/audit/export/{job.id}",
        )

        return StandardResponse.success(
            data=response.model_dump(),
            status_code=202,
            message="Audit export job accepted",
        ).make

    async def get_export_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status of an export job.

        Args:
            job_id: The job ID

        Returns:
            Standard response with job status
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            return StandardResponse.not_found(
                message="Export job not found",
                data={"error": "JOB_NOT_FOUND"},
            ).make

        response = AuditExportJobResponse(
            job_id=job.id,
            status=job.status,
            download_url=job.result_url,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

        return StandardResponse.success(
            data=response.model_dump(),
            message="Export job status retrieved",
        ).make

    @staticmethod
    def _compute_hash(entry_id: str, ts: datetime, actor: str,
                      action: str, target: str | None,
                      details: str | None, prev_hash: str | None) -> str:
        """
        Compute SHA-256 hash for audit entry.

        Args:
            entry_id: Audit entry ID
            ts: Timestamp
            actor: Actor identifier
            action: Action name
            target: Target identifier
            details: Details string
            prev_hash: Previous entry hash

        Returns:
            SHA-256 hash hex string
        """
        raw = (
            f"{entry_id}|{ts.isoformat()}|{actor}|{action}|"
            f"{target or ''}|{details or ''}|{prev_hash or ''}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
