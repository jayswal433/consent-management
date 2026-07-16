from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.core.security.audit_writer import write_audit_entry
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import ActorType, AuditAction, ConsentStatus
from app.repositories.job_repository import JobRepository
from app.schemas.dpdp.notification import (
    ExpiryReminderRequest,
    ExpiryReminderResponse,
    NotificationJobResponse,
    TestNotificationRequest,
    TestNotificationResponse,
)


class NotificationService:
    """Service for notification operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_repo = JobRepository(session)

    async def send_expiry_reminder(
        self,
        data: ExpiryReminderRequest,
        actor_id: str
    ) -> dict[str, Any]:
        """
        Send expiry reminders to users with expiring consents.

        Args:
            data: Expiry reminder request parameters
            actor_id: ID of user initiating the reminders

        Returns:
            Standard response with job ID and count
        """
        if data.channel not in ("email", "push", "sms"):
            return StandardResponse.bad_request(
                message="Invalid channel. Must be email, push, or sms.",
                data={"error": "INVALID_CHANNEL"},
            ).make

        expiry_date = datetime.now(UTC) + timedelta(days=data.within_days)

        stmt = (
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                and_(
                    DpdpConsent.form_id == data.form_id,
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                    DpdpConsent.expires_at <= expiry_date,
                    DpdpConsent.expires_at > datetime.now(UTC),
                )
            )
        )

        notified_count = await self.session.scalar(stmt) or 0

        job = await self.job_repo.create_job(
            job_type="notification",
            org_id=None,
            form_id=data.form_id,
            initiated_by=actor_id,
        )

        await self.job_repo.update_by_id(job.id, total=str(notified_count))

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.RECONSENT_NOTIFIED.value,
            target=data.form_id,
            version=data.channel,
            details=f"Notified {notified_count} users",
            org_id=None,
        )

        await self.session.commit()

        response = ExpiryReminderResponse(
            notified=notified_count,
            job_id=job.id,
        )

        return StandardResponse.success(
            data=response.model_dump(),
            status_code=202,
            message="Notification job accepted",
        ).make

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """
        Get the status of a notification job.

        Args:
            job_id: The job ID

        Returns:
            Standard response with job status
        """
        job = await self.job_repo.get_by_id(job_id)
        if not job:
            return StandardResponse.not_found(
                message="Notification job not found",
                data={"error": "JOB_NOT_FOUND"},
            ).make

        response = NotificationJobResponse(
            job_id=job.id,
            status=job.status,
            notified=int(job.total),
            failed=int(job.failed),
            completed_at=job.completed_at,
            error_message=job.error_message,
        )

        return StandardResponse.success(
            data=response.model_dump(),
            message="Notification job status retrieved",
        ).make

    async def send_test_notification(
        self,
        data: TestNotificationRequest,
        actor_id: str
    ) -> dict[str, Any]:
        """
        Send a test notification and return preview HTML.

        Args:
            data: Test notification request
            actor_id: ID of user initiating the test

        Returns:
            Standard response with preview HTML
        """
        if data.template not in ("expiry_reminder", "reconsent_required"):
            return StandardResponse.bad_request(
                message="Invalid template. Must be expiry_reminder or reconsent_required.",
                data={"error": "INVALID_TEMPLATE"},
            ).make

        preview_html = self._generate_preview_html(
            data.template,
            data.form_id,
            data.version
        )

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.RECONSENT_NOTIFIED.value,
            target=data.form_id,
            version=data.version,
            details=f"Test {data.template} sent to {data.user_id}",
            org_id=None,
        )

        await self.session.commit()

        response = TestNotificationResponse(
            sent=True,
            preview_html=preview_html,
        )

        return StandardResponse.success(
            data=response.model_dump(),
            message="Test notification sent successfully",
        ).make

    @staticmethod
    def _generate_preview_html(
        template: str,
        form_id: str,
        version: str
    ) -> str:
        """
        Generate preview HTML for notification template.

        Args:
            template: Template name
            form_id: Form ID
            version: Form version

        Returns:
            HTML preview string
        """
        if template == "expiry_reminder":
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Consent Expiry Reminder</h2>
                <p>Your consent for form <strong>{form_id}</strong> (version {version}) is expiring soon.</p>
                <p>Please renew your consent to continue using our services.</p>
                <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Renew Consent</a>
                <p style="margin-top: 20px; font-size: 12px; color: #999;">This is an automated message. Please do not reply.</p>
            </body>
            </html>
            """
        else:
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2>Consent Form Update</h2>
                <p>The consent form <strong>{form_id}</strong> (version {version}) has been updated.</p>
                <p>Please review the updated terms and provide your consent again.</p>
                <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Review & Reconsent</a>
                <p style="margin-top: 20px; font-size: 12px; color: #999;">This is an automated message. Please do not reply.</p>
            </body>
            </html>
            """
