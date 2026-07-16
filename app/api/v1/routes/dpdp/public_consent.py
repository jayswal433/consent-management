"""Public consent endpoints for inter-service / frontend use.

These routes are NOT protected by the DPDP RBAC JWT system.  They accept an
X-API-Key header issued by the organization. The user is identified solely by
the external_user_id (UUID from the calling service) — no local account required.
"""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.config.database import get_db_session
from app.core.responses.standard_response import StandardResponse
from app.core.security.api_key import require_org_api_key
from app.core.utils import constant_variable
from app.models.orm.consent_form import ConsentForm
from app.schemas.dpdp.consent import (
    PublicGrantConsentRequest,
    PublicWithdrawConsentRequest,
    ReconsentRequest,
    WithdrawConsentRequest,
)
from app.services.dpdp.consent_service import ConsentService

router = APIRouter(prefix="/public", tags=["Public Consent"])


def _extract_request_context(request: Request) -> tuple[str, str | None, str | None]:
    """Return (channel, user_agent, ip_address) derived from the HTTP request."""
    ua: str | None = request.headers.get("user-agent")

    # Derive channel from User-Agent: mobile browsers / apps → "mobile",
    # standard browser → "web", anything else (curl, SDK, no UA) → "api".
    if ua:
        ua_lower = ua.lower()
        if any(k in ua_lower for k in ("mobile", "android", "iphone", "ipad", "ipod")):
            channel = "mobile"
        elif any(k in ua_lower for k in ("mozilla", "chrome", "safari", "firefox", "opera", "edg")):
            channel = "web"
        else:
            channel = "api"
    else:
        channel = "api"

    # Prefer the leftmost (original client) IP from X-Forwarded-For when behind a proxy.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address: str | None = forwarded_for.split(",")[0].strip()
    elif request.client:
        ip_address = request.client.host
    else:
        ip_address = None

    return channel, ua, ip_address


@router.post(
    "/consents/accept",
    summary="Accept or re-consent",
    response_description="Granted consent with receipt token",
    status_code=201,
)
async def accept_consent(
    request: Request,
    payload: PublicGrantConsentRequest,
    session: AsyncSession = Depends(get_db_session),
    api_context: Annotated[dict, Depends(require_org_api_key)] = None,
) -> Any:
    """Accept or automatically re-consent on behalf of a data principal.

    A single endpoint handles both cases:

    - **No prior consent** — creates a fresh consent record.
    - **Consent exists, same active version** — returns 409 (already granted).
    - **Consent exists, older version** — supersedes the old record and grants
      the current active version (re-consent). The response will contain
      ``reconsented: true`` and ``previous_consent_id``.

    Pass the user's UUID from your auth microservice as ``external_user_id``.
    ``version`` is optional; when omitted the form's current active version is
    used automatically.  If supplied, it must match the active version.

    ``channel``, ``user_agent``, and ``ip_address`` are captured automatically
    from the HTTP request — do not include them in the request body.
    """
    try:
        org_id = api_context.get("org_id")

        form = await session.scalar(
            select(ConsentForm).where(ConsentForm.id == payload.form_id)
        )
        if not form or form.org_id != org_id:
            return StandardResponse.bad_request(
                message="Form does not belong to this organization"
            ).make

        if not form.active_version:
            return StandardResponse.bad_request(
                message="Form has no active version published yet"
            ).make

        if payload.version and payload.version != form.active_version:
            return StandardResponse.bad_request(
                message=f"Version '{payload.version}' is not the active version. "
                        f"Use '{form.active_version}' or omit version to auto-resolve."
            ).make

        resolved_payload = payload.model_copy(update={"version": form.active_version})

        channel, user_agent, ip_address = _extract_request_context(request)
        service = ConsentService(session)
        result = await service.public_accept_or_reconsent(
            resolved_payload,
            channel=channel,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await session.commit()

        message = "Re-consent recorded successfully" if result.get("reconsented") else "Consent accepted successfully"
        return StandardResponse.created(data=result, message=message).make

    except ValueError as e:
        error_msg = str(e)
        if error_msg == "CONSENT_ALREADY_GRANTED":
            return StandardResponse.conflict(
                message="Consent already granted for this version"
            ).make
        if error_msg == "FORM_VERSION_NOT_FOUND":
            return StandardResponse.not_found(message="Form version not found").make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        logger.exception("Unhandled error in accept_consent: %s", e)
        return StandardResponse.internal_error(
            message=f"Failed to accept consent: {str(e)}"
        ).make


@router.post(
    "/consents/reconsent",
    summary="Re-consent to a new form version",
    response_description="New consent with superseded previous consent details",
    status_code=201,
)
async def reconsent(
    payload: ReconsentRequest,
    session: AsyncSession = Depends(get_db_session),
    api_context: Annotated[dict, Depends(require_org_api_key)] = None,
) -> Any:
    """Re-consent when a form version has changed.

    If the user previously granted consent, that record is marked 'superseded'
    and a new consent record is created for ``new_version``.

    The response includes both ``previous_consent_id`` (the superseded record)
    and ``new_consent_id`` (the fresh grant).
    The form must belong to the organization that issued the API key.
    """
    try:
        org_id = api_context.get("org_id")

        form = await session.scalar(
            select(ConsentForm).where(ConsentForm.id == payload.form_id)
        )
        if not form or form.org_id != org_id:
            return StandardResponse.bad_request(
                message="Form does not belong to this organization"
            ).make

        service = ConsentService(session)
        result = await service.public_reconsent(payload)
        await session.commit()
        return StandardResponse.created(
            data=result,
            message="Re-consent recorded successfully",
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "FORM_VERSION_NOT_FOUND":
            return StandardResponse.not_found(message="Form version not found").make
        if error_msg == "CONSENT_ALREADY_GRANTED":
            return StandardResponse.conflict(
                message="Consent already granted for this version"
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        logger.exception("Unhandled error in reconsent: %s", e)
        return StandardResponse.internal_error(
            message=f"Failed to re-consent: {str(e)}"
        ).make


@router.get(
    "/consents/status",
    summary="Check consent status against the organization's active form",
    response_description="Consent validity, action required, and form/version details",
)
async def check_consent_status(
    external_user_id: str = Query(
        ..., description="UUID from the external auth microservice"
    ),
    form_code: str | None = Query(
        None,
        description=(
            "Form code — required only when the organization has more than one "
            "active consent form. Omit if the org has a single active form."
        ),
    ),
    session: AsyncSession = Depends(get_db_session),
    api_context: Annotated[dict, Depends(require_org_api_key)] = None,
) -> Any:
    """Check whether an external user has accepted the organization's active consent form.

    Returns ``status: true`` only when the user has an active consent that
    matches the form's current active version.  All other cases
    (never consented, consented to an older version, withdrawn, expired)
    return ``status: false``.

    The active form is resolved automatically from the API key — no
    ``form_id`` is needed.  Pass ``form_code`` only when the organization
    has more than one active form.
    """
    try:
        org_id = api_context.get("org_id")
        service = ConsentService(session)
        result = await service.check_consent_for_org(
            user_id=external_user_id,
            org_id=org_id,
            form_code=form_code,
        )
        return StandardResponse.success(
            data=result,
            message="Consent status retrieved",
            status_code=constant_variable.HTTP_200_OK,
        ).make
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "NO_ACTIVE_FORM":
            return StandardResponse.not_found(
                message="No active consent form found for this organization."
            ).make
        if error_msg == "MULTIPLE_ACTIVE_FORMS":
            return StandardResponse.bad_request(
                message=(
                    "This organization has multiple active forms. "
                    "Pass form_code as a query parameter to specify which one."
                )
            ).make
        if error_msg == "NO_ACTIVE_VERSION":
            return StandardResponse.bad_request(
                message="The active form has no published version yet."
            ).make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        logger.exception("Unhandled error in check_consent_status: %s", e)
        return StandardResponse.internal_error(
            message=f"Failed to check consent status: {str(e)}"
        ).make


@router.post(
    "/consents/{consent_id}/withdraw",
    summary="Withdraw consent",
    response_description="Withdrawal confirmation",
)
async def withdraw_consent(
    consent_id: str,
    payload: PublicWithdrawConsentRequest,
    external_user_id: str = Query(
        ...,
        description="External user UUID — must match the owner of this consent",
    ),
    session: AsyncSession = Depends(get_db_session),
    api_context: Annotated[dict, Depends(require_org_api_key)] = None,
) -> Any:
    """Withdraw a previously granted consent.

    ``external_user_id`` must match the user who originally granted the
    consent. The consent must belong to a form owned by the organization that
    issued the API key.
    Admins should use the RBAC-protected ``/consents/{id}/withdraw`` endpoint.
    """
    try:
        org_id = api_context.get("org_id")
        service = ConsentService(session)

        consent = await service.repo.get_by_id(consent_id)
        if not consent:
            return StandardResponse.not_found(message="Consent not found").make

        if consent.user_id != external_user_id:
            return StandardResponse.forbidden(
                message="You are not authorized to withdraw this consent"
            ).make

        form = await session.scalar(
            select(ConsentForm).where(ConsentForm.id == consent.form_id)
        )
        if not form or form.org_id != org_id:
            return StandardResponse.bad_request(
                message="Consent does not belong to this organization"
            ).make

        withdraw_payload = WithdrawConsentRequest(
            reason=payload.reason,
            channel=payload.channel,
        )
        result = await service.withdraw_consent(
            consent_id=consent_id,
            data=withdraw_payload,
            actor_id=external_user_id,
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
            return StandardResponse.not_found(message="Consent not found").make
        return StandardResponse.bad_request(message=error_msg).make
    except Exception as e:
        logger.exception("Unhandled error in withdraw_consent: %s", e)
        return StandardResponse.internal_error(
            message=f"Failed to withdraw consent: {str(e)}"
        ).make
