from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GrantConsentRequest(BaseModel):
    """Request to grant consent for a form."""

    user_id: str = Field(..., min_length=1, max_length=36)
    form_id: str = Field(..., min_length=1, max_length=36)
    version: str = Field(..., min_length=1, max_length=10)
    optional_fields: Optional[list[str]] = Field(
        None, description="Field names user selected"
    )
    channel: str = Field("web", pattern="^(web|mobile|api)$")
    user_agent: Optional[str] = Field(None, max_length=500)
    ip_address: Optional[str] = Field(None, max_length=45)


class ConsentCheckRequest(BaseModel):
    """Request to check if consent exists."""

    user_id: str = Field(..., min_length=1, max_length=36)
    form_id: str = Field(..., min_length=1, max_length=36)


class ConsentCheckResponse(BaseModel):
    """Response for consent check."""

    has_consent: bool
    version: Optional[str] = None
    reconsent_required: bool
    status: Optional[str] = None


class WithdrawConsentRequest(BaseModel):
    """Request to withdraw consent."""

    reason: Optional[str] = Field(None, max_length=500)
    channel: str = Field("web", pattern="^(web|mobile|api)$")


class DeclineConsentRequest(BaseModel):
    """Request to decline consent."""

    user_id: str = Field(..., min_length=1, max_length=36)
    form_id: str = Field(..., min_length=1, max_length=36)
    version: str = Field(..., min_length=1, max_length=10)
    channel: str = Field("web", pattern="^(web|mobile|api)$")


class ConsentResponse(BaseModel):
    """Full consent record response."""

    id: str
    user_id: str
    form_id: str
    version: str
    status: str
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    optional_fields: Optional[list[str]] = None
    receipt_token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentListItem(BaseModel):
    """Simplified consent item for list responses."""

    id: str
    user_id: str
    form_id: str
    version: str
    status: str
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConsentGrantResponse(BaseModel):
    """Response when consent is granted."""

    id: str
    status: str
    granted_at: datetime
    expires_at: datetime
    receipt_token: str
    reconsented: bool = False
    previous_consent_id: Optional[str] = None


class ConsentListResponse(BaseModel):
    """Paginated list of consents."""

    items: list[ConsentListItem]
    total: int
    page: int
    limit: int


class WithdrawConsentResponse(BaseModel):
    """Response when consent is withdrawn."""

    status: str
    withdrawn_at: datetime
    withdrawal_receipt_id: str


class DeclineConsentResponse(BaseModel):
    """Response when consent is declined."""

    logged: bool
    audit_id: str


# ---------------------------------------------------------------------------
# Public / inter-service schemas (used by external microservice callers)
# ---------------------------------------------------------------------------


class PublicGrantConsentRequest(BaseModel):
    """Accept consent from a data principal identified by an external UUID.

    The external_user_id is the user UUID from the calling microservice.
    This service stores it directly without requiring a local account.
    channel, user_agent, and ip_address are NOT accepted in the payload —
    they are extracted automatically from the HTTP request context.

    version is optional — if omitted the form's current active_version is used.
    If provided it must match the form's active_version exactly.
    """

    external_user_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        description="UUID of the user from the external auth microservice",
    )
    form_id: str = Field(..., min_length=1, max_length=36)
    version: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10,
        description="Form version to consent to; defaults to the form's active version",
    )
    optional_fields: Optional[list[str]] = Field(
        None, description="Opted-in optional field names"
    )


class ReconsentRequest(BaseModel):
    """Re-consent: supersede the current consent and grant a new version.

    Use this when a form version changes and the user must re-consent to
    the updated terms.  The previous granted consent is marked 'superseded'
    and a fresh consent record is created for new_version.
    """

    external_user_id: str = Field(..., min_length=1, max_length=36)
    form_id: str = Field(..., min_length=1, max_length=36)
    new_version: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="New form version the user is consenting to",
    )
    optional_fields: Optional[list[str]] = None
    channel: str = Field("web", pattern="^(web|mobile|api)$")
    user_agent: Optional[str] = Field(None, max_length=500)
    ip_address: Optional[str] = Field(None, max_length=45)


class ReconsentResponse(BaseModel):
    """Response for a re-consent operation."""

    previous_consent_id: Optional[str] = None
    new_consent_id: str
    status: str
    granted_at: datetime
    expires_at: datetime
    receipt_token: str


class PublicWithdrawConsentRequest(BaseModel):
    """Withdraw a consent record (public / external-user path)."""

    reason: Optional[str] = Field(None, max_length=500)
    channel: str = Field("web", pattern="^(web|mobile|api)$")


class PublicConsentStatusResponse(BaseModel):
    """Response for the org-scoped consent status check.

    status is True only when the user has an active, non-expired consent
    that matches the organization's current active form version.
    All other cases (no consent, old version, withdrawn, expired) return False.
    """

    status: bool
    consent_id: Optional[str] = None
    form_id: str
    active_version: Optional[str] = None
    user_consented_version: Optional[str] = None
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
