from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExpiryReminderRequest(BaseModel):
    """Request to send expiry reminder notifications."""

    form_id: str = Field(..., description="Consent form ID")
    within_days: int = Field(
        ..., ge=1, description="Send to consents expiring within N days"
    )
    channel: str = Field(
        "email", description="Notification channel: email|push|sms"
    )


class ExpiryReminderResponse(BaseModel):
    """Async notification job response."""

    notified: int
    job_id: str
    message: str = "Notification job accepted"


class NotificationJobResponse(BaseModel):
    """Notification job status response."""

    job_id: str
    status: str
    notified: int
    failed: int
    completed_at: datetime | None = None
    error_message: str | None = None


class TestNotificationRequest(BaseModel):
    """Test notification request."""

    user_id: str = Field(..., description="Target user ID")
    template: str = Field(
        ...,
        description="Template name: expiry_reminder|reconsent_required"
    )
    form_id: str = Field(..., description="Consent form ID")
    version: str = Field(..., description="Form version")


class TestNotificationResponse(BaseModel):
    """Test notification response with preview."""

    sent: bool
    preview_html: str
