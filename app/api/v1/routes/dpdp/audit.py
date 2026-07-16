from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, require_permission
from app.schemas.dpdp.audit import AuditExportRequest
from app.services.dpdp.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def list_audit_logs(
    actor_type: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    form_id: Annotated[str | None, Query()] = None,
    user_id: Annotated[str | None, Query()] = None,
    from_date: Annotated[str | None, Query()] = None,
    to_date: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_AUDIT_LOG))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """List audit logs with optional filters."""
    service = AuditService(session)
    return await service.list_audit(
        actor_type=actor_type,
        action=action,
        form_id=form_id,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )


@router.post("/export")
async def start_audit_export(
    data: AuditExportRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))],
    session: AsyncSession = Depends(get_db_session),
):
    """Start an async audit log export."""
    actor_id = token_data.get("sub")
    service = AuditService(session)
    return await service.start_export(data, actor_id)


@router.get("/export/{job_id}")
async def get_export_status(
    job_id: str,
    token_data: Annotated[dict, Depends(require_permission(Permission.EXPORT_AUDIT_LOG))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get the status of an audit export job."""
    service = AuditService(session)
    return await service.get_export_status(job_id)


@router.get("/{audit_id}")
async def get_audit_entry(
    audit_id: str,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_AUDIT_LOG))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a single audit log entry with hash chain details."""
    service = AuditService(session)
    return await service.get_audit_entry(audit_id)
