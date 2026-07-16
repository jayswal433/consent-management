from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, require_permission
from app.schemas.dpdp.notification import (
    ExpiryReminderRequest,
    TestNotificationRequest,
)
from app.services.dpdp.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/expiry-reminder")
async def send_expiry_reminder(
    data: ExpiryReminderRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.TRIGGER_NOTIFICATIONS))],
    session: AsyncSession = Depends(get_db_session),
):
    """Send expiry reminders to users with expiring consents."""
    actor_id = token_data.get("sub")
    service = NotificationService(session)
    return await service.send_expiry_reminder(data, actor_id)


@router.get("/jobs/{job_id}")
async def get_notification_job_status(
    job_id: str,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ALL_CONSENTS))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get the status of a notification job."""
    service = NotificationService(session)
    return await service.get_job_status(job_id)


@router.post("/test")
async def send_test_notification(
    data: TestNotificationRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.APPROVE_PUBLISH_VERSION))],
    session: AsyncSession = Depends(get_db_session),
):
    """Send a test notification and return preview HTML."""
    actor_id = token_data.get("sub")
    service = NotificationService(session)
    return await service.send_test_notification(data, actor_id)
