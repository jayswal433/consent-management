from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.responses.standard_response import StandardResponse
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.core.utils import constant_variable
from app.schemas.dpdp.consent import (
    DeclineConsentRequest,
    GrantConsentRequest,
    WithdrawConsentRequest,
)
from app.services.dpdp.consent_service import ConsentService

router = APIRouter(prefix="/consents", tags=["Consents"])


@router.get(
    "",
    summary="List all consents",
    response_description="List of consents with pagination",
)
async def list_consents(
    user_id: str | None = Query(None),
    form_id: str | None = Query(None),
    version: str | None = Query(None),
    status: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.VIEW_ALL_CONSENTS)),
) -> Any:
    """
    List consents with optional filters.

    Query Parameters:
    - user_id: Filter by user ID
    - form_id: Filter by form ID
    - version: Filter by version
    - status: Filter by status
    - from_date: ISO datetime string
    - to_date: ISO datetime string
    - page: Page number (1-indexed)
    - limit: Items per page (1-100)
    """
    try:
        service = ConsentService(session)
        result = await service.list_consents(
            user_id=user_id,
            form_id=form_id,
            version=version,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            limit=limit,
        )
        return StandardResponse.success(
            data=result,
            message="Consents retrieved successfully",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to list consents: {str(e)}"
        ).make


@router.post(
    "",
    summary="Grant consent",
    response_description="Granted consent with receipt token",
    status_code=201,
)
async def grant_consent(
    payload: GrantConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.GRANT_CONSENT)),
) -> Any:
    """Grant consent for a user on a form."""
    try:
        service = ConsentService(session)
        actor_id = token_data.get("sub", "system")
        result = await service.grant_consent(payload, actor_id)
        await session.commit()
        return StandardResponse.created(
            data=result,
            message="Consent granted successfully",
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "CONSENT_ALREADY_GRANTED":
            return StandardResponse.conflict(
                message="Consent already granted for this version"
            ).make
        elif error_msg == "FORM_VERSION_NOT_FOUND":
            return StandardResponse.not_found(
                message="Form version not found"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to grant consent: {str(e)}"
        ).make


@router.post(
    "/check",
    summary="Check consent status",
    response_description="Consent check result",
)
async def check_consent(
    payload: DeclineConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.CHECK_CONSENT_SERVICE)),
) -> Any:
    """
    Check if user has valid consent for a form.

    Returns whether consent exists, version, and if reconsent is required.
    """
    try:
        service = ConsentService(session)
        result = await service.check_consent(
            user_id=payload.user_id,
            form_id=payload.form_id,
        )
        return StandardResponse.success(
            data=result,
            message="Consent check completed",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to check consent: {str(e)}"
        ).make


@router.get(
    "/{consent_id}",
    summary="Get consent details",
    response_description="Consent record",
)
async def get_consent(
    consent_id: str,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.VIEW_OWN_CONSENTS)),
) -> Any:
    """Get details of a specific consent."""
    try:
        service = ConsentService(session)
        requester_id = token_data.get("sub", "")
        requester_role = token_data.get("role", "")
        result = await service.get_consent(
            consent_id=consent_id,
            requester_id=requester_id,
            requester_role=requester_role,
        )
        return StandardResponse.success(
            data=result,
            message="Consent retrieved successfully",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "RESOURCE_NOT_FOUND":
            return StandardResponse.not_found(
                message="Consent not found"
            ).make
        elif error_msg == "INSUFFICIENT_SCOPE":
            return StandardResponse.forbidden(
                message="Access denied to this consent"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to get consent: {str(e)}"
        ).make


@router.post(
    "/{consent_id}/withdraw",
    summary="Withdraw consent",
    response_description="Withdrawal confirmation",
)
async def withdraw_consent(
    consent_id: str,
    payload: WithdrawConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.WITHDRAW_CONSENT)),
) -> Any:
    """Withdraw an existing consent."""
    try:
        service = ConsentService(session)
        actor_id = token_data.get("sub", "system")
        result = await service.withdraw_consent(
            consent_id=consent_id,
            data=payload,
            actor_id=actor_id,
        )
        await session.commit()
        return StandardResponse.success(
            data=result,
            message="Consent withdrawn successfully",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "RESOURCE_NOT_FOUND":
            return StandardResponse.not_found(
                message="Consent not found"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to withdraw consent: {str(e)}"
        ).make


@router.post(
    "/{consent_id}/decline",
    summary="Decline consent",
    response_description="Decline logged",
)
async def decline_consent(
    consent_id: str,
    payload: DeclineConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.GRANT_CONSENT)),
) -> Any:
    """Decline consent (logs action without creating record)."""
    try:
        service = ConsentService(session)
        actor_id = token_data.get("sub", "system")
        result = await service.decline_consent(
            data=payload,
            actor_id=actor_id,
        )
        await session.commit()
        return StandardResponse.success(
            data=result,
            message="Decline logged successfully",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to log decline: {str(e)}"
        ).make


@router.get(
    "/{consent_id}/receipt",
    summary="Download consent receipt",
    response_description="Consent receipt",
)
async def get_receipt(
    consent_id: str,
    format: str = Query("json", pattern="^(json|pdf)$"),
    session: AsyncSession = Depends(get_db_session),
    token_data: dict[str, Any] = Depends(require_permission(Permission.DOWNLOAD_CONSENT_RECEIPT)),
) -> Any:
    """
    Get consent receipt.

    Query Parameters:
    - format: Response format (json or pdf; currently only json supported)
    """
    try:
        service = ConsentService(session)
        requester_id = token_data.get("sub", "")
        requester_role = token_data.get("role", "")
        result = await service.get_receipt(
            consent_id=consent_id,
            requester_id=requester_id,
            requester_role=requester_role,
        )
        return StandardResponse.success(
            data=result,
            message="Receipt retrieved successfully",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "RESOURCE_NOT_FOUND":
            return StandardResponse.not_found(
                message="Consent not found"
            ).make
        elif error_msg == "INSUFFICIENT_SCOPE":
            return StandardResponse.forbidden(
                message="Access denied to this receipt"
            ).make
        elif error_msg == "RECEIPT_NOT_AVAILABLE":
            return StandardResponse.not_found(
                message="Receipt not available"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        return StandardResponse.internal_error(
            message=f"Failed to get receipt: {str(e)}"
        ).make
