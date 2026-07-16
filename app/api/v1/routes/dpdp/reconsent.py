from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.responses.standard_response import StandardResponse
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.core.utils import constant_variable
from app.schemas.dpdp.reconsent import (
    BulkRevokeRequest,
    ReconsentNotifyRequest,
)
from app.services.dpdp.reconsent_service import ReconsentService

router = APIRouter(prefix="/reconsent", tags=["Reconsent"])


@router.get(
    "/pending",
    summary="Get pending reconsent",
    response_description="Users requiring reconsent",
)
async def get_pending_reconsent(
    form_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.VIEW_ALL_CONSENTS)),
) -> Any:
    """
    Get users with pending reconsent requirements.

    Query Parameters:
    - form_id: Filter by form ID (required)
    - page: Page number (1-indexed)
    - limit: Items per page (1-100)
    """
    try:
        if not form_id:
            return StandardResponse.bad_request(
                message="form_id query parameter is required"
            ).make

        service = ReconsentService(session)
        result = await service.get_pending_reconsent(
            form_id=form_id,
            page=page,
            limit=limit,
        )
        return StandardResponse.success(
            data=result,
            message="Pending reconsent users retrieved",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "FORM_NOT_FOUND":
            return StandardResponse.not_found(
                message="Form not found"
            ).make
        elif error_msg == "NO_ACTIVE_VERSION":
            return StandardResponse.bad_request(
                message="Form has no active version"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to get pending reconsent: {str(e)}"
        ).make


@router.post(
    "/notify",
    summary="Notify users for reconsent",
    response_description="Notification job created",
    status_code=201,
)
async def notify_users(
    payload: ReconsentNotifyRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.TRIGGER_NOTIFICATIONS)),
) -> Any:
    """
    Notify users about reconsent requirement.

    If user_ids is not provided, all users with pending reconsent are notified.
    """
    try:
        service = ReconsentService(session)
        actor_id = token_data.get("sub", "system")
        result = await service.notify_users(
            form_id=payload.form_id,
            version=payload.version,
            user_ids=payload.user_ids,
            actor_id=actor_id,
        )
        await session.commit()
        return StandardResponse.created(
            data=result,
            message="Notification job created successfully",
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "FORM_NOT_FOUND":
            return StandardResponse.not_found(
                message="Form not found"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to notify users: {str(e)}"
        ).make


@router.post(
    "/bulk-revoke",
    summary="Bulk revoke consents",
    response_description="Revoke operation results",
)
async def bulk_revoke(
    payload: BulkRevokeRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.BULK_REVOKE)),
) -> Any:
    """
    Bulk revoke consents for stale versions.

    By default runs as dry_run=True. Set dry_run=False to actually revoke.
    """
    try:
        service = ReconsentService(session)
        actor_id = token_data.get("sub", "system")
        result = await service.bulk_revoke(
            form_id=payload.form_id,
            older_than=payload.older_than,
            dry_run=payload.dry_run,
            actor_id=actor_id,
        )
        if not payload.dry_run:
            await session.commit()
        return StandardResponse.success(
            data=result,
            message="Bulk revoke operation completed",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "FORM_NOT_FOUND":
            return StandardResponse.not_found(
                message="Form not found"
            ).make
        elif error_msg == "NO_ACTIVE_VERSION":
            return StandardResponse.bad_request(
                message="Form has no active version"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to revoke consents: {str(e)}"
        ).make


@router.get(
    "/jobs/{job_id}",
    summary="Get async job status",
    response_description="Job status details",
)
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.VIEW_ALL_CONSENTS)),
) -> Any:
    """Get status of an async reconsent job."""
    try:
        service = ReconsentService(session)
        result = await service.get_job_status(job_id=job_id)
        return StandardResponse.success(
            data=result,
            message="Job status retrieved",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "JOB_NOT_FOUND":
            return StandardResponse.not_found(
                message="Job not found"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to get job status: {str(e)}"
        ).make
