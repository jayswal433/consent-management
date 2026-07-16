from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReconsentPendingItem(BaseModel):
    """Item for pending reconsent."""

    user_id: str
    form_id: str
    current_version: str
    required_version: str


class ReconsentPendingResponse(BaseModel):
    """Response for pending reconsent list."""

    items: list[ReconsentPendingItem]
    total: int
    page: int
    limit: int


class ReconsentNotifyRequest(BaseModel):
    """Request to notify users about reconsent."""

    form_id: str = Field(..., min_length=1, max_length=36)
    version: str = Field(..., min_length=1, max_length=10)
    user_ids: Optional[list[str]] = Field(
        None, description="User IDs to notify; None means all pending"
    )
    channel: str = Field("email", pattern="^(email|push|sms)$")


class ReconsentNotifyResponse(BaseModel):
    """Response when reconsent notification is triggered."""

    notified: int
    job_id: str


class BulkRevokeRequest(BaseModel):
    """Request to bulk revoke consents."""

    form_id: str = Field(..., min_length=1, max_length=36)
    older_than: datetime = Field(
        ..., description="ISO datetime: revoke consents older than this"
    )
    dry_run: bool = Field(True, description="If True, don't actually revoke")


class BulkRevokeResponse(BaseModel):
    """Response for bulk revoke operation."""

    revoked: int
    dry_run: bool
    affected_users: list[str]


class JobStatusResponse(BaseModel):
    """Response for async job status."""

    job_id: str
    status: str
    notified: int
    failed: int
    completed_at: Optional[datetime] = None
