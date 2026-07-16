from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogItem(BaseModel):
    """Audit log entry response schema."""

    id: str
    ts: datetime
    actor: str
    actor_type: str
    action: str
    target: str | None = None
    version: str | None = None
    details: str | None = None
    hash: str
    org_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogDetailItem(AuditLogItem):
    """Audit log entry with tamper verification details."""

    prev_hash: str | None = None


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    items: list[AuditLogItem]
    total: int
    page: int
    limit: int


class AuditExportRequest(BaseModel):
    """Request to export audit logs."""

    form_id: str | None = Field(
        None, description="Filter by form ID"
    )
    from_date: str | None = Field(
        None, description="ISO datetime filter start"
    )
    to_date: str | None = Field(
        None, description="ISO datetime filter end"
    )
    format: str = Field(
        "jsonl", description="Export format: csv or jsonl"
    )


class AuditExportResponse(BaseModel):
    """Async export job response."""

    job_id: str
    download_url: str
    message: str = "Export job accepted"


class AuditExportJobResponse(BaseModel):
    """Export job status response."""

    job_id: str
    status: str
    download_url: str | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
