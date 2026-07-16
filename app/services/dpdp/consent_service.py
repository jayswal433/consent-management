from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import httpx
except ImportError:
    httpx = None

from app.core.security.audit_writer import write_audit_entry
from app.core.security.crypto import (
    decrypt_field,
    encrypt_field,
    get_dek,
    get_hmac_key,
    hmac_sha256_sign,
    sha256_hash,
)
from app.models.orm.consent_form import ConsentForm
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import AuditAction, ConsentStatus
from app.models.orm.dpdp_user import DpdpUser
from app.models.orm.form_version import FormVersion
from app.models.orm.org import Org
from app.repositories.dpdp_consent_repository import DpdpConsentRepository
from app.schemas.dpdp.consent import (
    ConsentCheckResponse,
    ConsentGrantResponse,
    ConsentListResponse,
    DeclineConsentRequest,
    DeclineConsentResponse,
    GrantConsentRequest,
    PublicGrantConsentRequest,
    ReconsentRequest,
    WithdrawConsentRequest,
    WithdrawConsentResponse,
)


class ConsentService:
    """Service for managing consent operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DpdpConsentRepository(session)

    async def list_consents(
        self,
        user_id: str | None,
        form_id: str | None,
        version: str | None,
        status: str | None,
        from_date: str | None,
        to_date: str | None,
        page: int,
        limit: int,
    ) -> dict[str, Any]:
        """
        List consents with optional filters.

        Args:
            user_id: Filter by user ID.
            form_id: Filter by form ID.
            version: Filter by version.
            status: Filter by status.
            from_date: ISO datetime string for start date.
            to_date: ISO datetime string for end date.
            page: Page number (1-indexed).
            limit: Items per page.

        Returns:
            Dictionary with items, total, page, limit.
        """
        from_datetime = None
        to_datetime = None

        if from_date:
            from_datetime = datetime.fromisoformat(from_date)
        if to_date:
            to_datetime = datetime.fromisoformat(to_date)

        consents, total = await self.repo.list_consents(
            user_id=user_id,
            form_id=form_id,
            version=version,
            status=status,
            from_date=from_datetime,
            to_date=to_datetime,
            page=page,
            limit=limit,
        )

        items = [
            {
                "id": c.id,
                "user_id": c.user_id,
                "form_id": c.form_id,
                "version": c.version,
                "status": c.status,
                "granted_at": c.granted_at,
                "expires_at": c.expires_at,
            }
            for c in consents
        ]

        response = ConsentListResponse(
            items=items, total=total, page=page, limit=limit
        )
        return response.model_dump()

    async def grant_consent(
        self, data: GrantConsentRequest, actor_id: str
    ) -> dict[str, Any]:
        """
        Grant consent for a form.

        Args:
            data: Consent grant request data.
            actor_id: ID of the actor granting consent.

        Returns:
            Granted consent response.

        Raises:
            ValueError: If consent already exists or form version not found.
        """
        existing = await self.repo.get_by_user_form_version(
            user_id=data.user_id,
            form_id=data.form_id,
            version=data.version,
        )
        if existing and existing.status == ConsentStatus.GRANTED.value:
            raise ValueError("CONSENT_ALREADY_GRANTED")

        form_version = await self.session.scalar(
            select(FormVersion).where(
                and_(
                    FormVersion.form_id == data.form_id,
                    FormVersion.version == data.version,
                )
            )
        )
        if not form_version:
            raise ValueError("FORM_VERSION_NOT_FOUND")

        now = datetime.now(UTC)
        expiry_days = int(form_version.expiry_days)
        expires_at = now + timedelta(days=expiry_days)

        optional_fields_json = json.dumps(data.optional_fields or [])
        encrypted_fields = encrypt_field(optional_fields_json, get_dek())

        daily_salt = now.strftime("%Y-%m-%d")
        ip_hash = (
            sha256_hash(data.ip_address, salt=daily_salt)
            if data.ip_address
            else None
        )
        user_agent_hash = (
            sha256_hash(data.user_agent, salt=daily_salt)
            if data.user_agent
            else None
        )

        consent_id = str(uuid.uuid4())
        receipt_payload = {
            "jti": str(uuid.uuid4()),
            "consent_id": consent_id,
            "user_id": data.user_id,
            "form_id": data.form_id,
            "version": data.version,
            "granted_at": now.isoformat(),
            "type": "consent_receipt",
            "iat": int(now.timestamp()),
        }
        receipt_token = hmac_sha256_sign(receipt_payload, get_hmac_key())

        consent = DpdpConsent(
            id=consent_id,
            user_id=data.user_id,
            form_id=data.form_id,
            version=data.version,
            status=ConsentStatus.GRANTED.value,
            optional_fields=encrypted_fields,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            channel=data.channel,
            granted_at=now,
            expires_at=expires_at,
            receipt_token=receipt_token,
        )

        self.session.add(consent)
        await self.session.flush()
        await self.session.refresh(consent)

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type="user" if actor_id == data.user_id else "admin",
            action=AuditAction.CONSENT_GRANTED.value,
            target=data.user_id,
            version=data.version,
            details=f"form_id={data.form_id}",
        )

        response = ConsentGrantResponse(
            id=consent.id,
            status=consent.status,
            granted_at=consent.granted_at,
            expires_at=consent.expires_at,
            receipt_token=receipt_token,
        )
        return response.model_dump()

    async def get_consent(
        self, consent_id: str, requester_id: str, requester_role: str
    ) -> dict[str, Any]:
        """
        Get a consent record.

        Args:
            consent_id: Consent ID.
            requester_id: ID of the requester.
            requester_role: Role of the requester.

        Returns:
            Consent record as dictionary.

        Raises:
            ValueError: If consent not found or unauthorized.
        """
        consent = await self.repo.get_by_id(consent_id)
        if not consent:
            raise ValueError("RESOURCE_NOT_FOUND")

        allow_decrypt = (
            requester_role == "super_admin"
            or requester_role == "org_admin"
            or requester_id == consent.user_id
        )

        optional_fields = None
        if allow_decrypt and consent.optional_fields:
            try:
                fields_json = decrypt_field(consent.optional_fields, get_dek())
                optional_fields = json.loads(fields_json)
            except Exception:
                optional_fields = None

        return {
            "id": consent.id,
            "user_id": consent.user_id,
            "form_id": consent.form_id,
            "version": consent.version,
            "status": consent.status,
            "granted_at": consent.granted_at,
            "expires_at": consent.expires_at,
            "optional_fields": optional_fields,
            "receipt_token": consent.receipt_token if allow_decrypt else None,
        }

    async def check_consent(
        self, user_id: str, form_id: str
    ) -> dict[str, Any]:
        """
        Check if user has valid consent for a form.

        Args:
            user_id: User ID.
            form_id: Form ID.

        Returns:
            Consent check response.
        """
        active_consent = await self.repo.get_active_consent(user_id, form_id)

        if not active_consent:
            response = ConsentCheckResponse(
                has_consent=False,
                version=None,
                reconsent_required=False,
                status=None,
            )
            return response.model_dump()

        from app.models.orm.consent_form import ConsentForm

        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == form_id)
        )

        reconsent_required = False
        if form and form.active_version:
            reconsent_required = active_consent.version != form.active_version

        response = ConsentCheckResponse(
            has_consent=True,
            version=active_consent.version,
            reconsent_required=reconsent_required,
            status=active_consent.status,
        )
        return response.model_dump()

    async def check_consent_for_org(
        self,
        user_id: str,
        org_id: str,
        form_code: str | None = None,
    ) -> dict[str, Any]:
        """Check whether a user has valid consent for the org's active form.

        Resolves the active form automatically from the org (identified by the
        caller's API key).  No form_id is required from the caller.

        Args:
            user_id:   External user UUID from the calling microservice.
            org_id:    Organisation UUID derived from the API key.
            form_code: Optional form code when the org has more than one active
                       form; raises MULTIPLE_ACTIVE_FORMS if omitted in that case.

        Returns:
            Dict matching PublicConsentStatusResponse with action, form details,
            and the user's current consent state.

        Raises:
            ValueError: NO_ACTIVE_FORM | MULTIPLE_ACTIVE_FORMS | NO_ACTIVE_VERSION
        """
        query = select(ConsentForm).where(
            and_(ConsentForm.org_id == org_id, ConsentForm.status == "active")
        )
        if form_code:
            query = query.where(ConsentForm.code == form_code)

        result = await self.session.execute(query)
        forms = result.scalars().all()

        if not forms:
            raise ValueError("NO_ACTIVE_FORM")
        if len(forms) > 1:
            raise ValueError("MULTIPLE_ACTIVE_FORMS")

        form = forms[0]

        if not form.active_version:
            raise ValueError("NO_ACTIVE_VERSION")

        active_consent = await self.repo.get_active_consent(user_id, form.id)

        if not active_consent:
            return {
                "status": False,
                "consent_id": None,
                "form_id": form.id,
                "active_version": form.active_version,
                "user_consented_version": None,
                "granted_at": None,
                "expires_at": None,
            }

        # True only when the user's consent is on the current active version.
        on_active_version = active_consent.version == form.active_version

        return {
            "status": on_active_version,
            "consent_id": active_consent.id,
            "form_id": form.id,
            "active_version": form.active_version,
            "user_consented_version": active_consent.version,
            "granted_at": active_consent.granted_at,
            "expires_at": active_consent.expires_at,
        }

    async def withdraw_consent(
        self, consent_id: str, data: WithdrawConsentRequest, actor_id: str
    ) -> dict[str, Any]:
        """
        Withdraw consent.

        Args:
            consent_id: Consent ID.
            data: Withdraw request data.
            actor_id: ID of the actor withdrawing.

        Returns:
            Withdraw response.

        Raises:
            ValueError: If consent not found.
        """
        consent = await self.repo.get_by_id(consent_id)
        if not consent:
            raise ValueError("RESOURCE_NOT_FOUND")

        now = datetime.now(UTC)
        withdrawal_receipt_id = str(uuid.uuid4())

        await self.repo.update_by_id(
            consent_id,
            status=ConsentStatus.WITHDRAWN.value,
            withdrawn_at=now,
            withdrawal_receipt_id=withdrawal_receipt_id,
        )

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type="user" if actor_id == consent.user_id else "admin",
            action=AuditAction.CONSENT_WITHDRAWN.value,
            target=consent.user_id,
            version=consent.version,
            details=f"form_id={consent.form_id}, reason={data.reason or 'none'}",
        )

        response = WithdrawConsentResponse(
            status=ConsentStatus.WITHDRAWN.value,
            withdrawn_at=now,
            withdrawal_receipt_id=withdrawal_receipt_id,
        )
        return response.model_dump()

    async def decline_consent(
        self, data: DeclineConsentRequest, actor_id: str
    ) -> dict[str, Any]:
        """
        Decline consent (no record created).

        Args:
            data: Decline request data.
            actor_id: ID of the actor declining.

        Returns:
            Decline response with audit ID.
        """
        audit_entry = await write_audit_entry(
            self.session,
            actor=actor_id if actor_id else data.user_id,
            actor_type="user",
            action=AuditAction.CONSENT_DECLINED.value,
            target=data.user_id,
            version=data.version,
            details=f"form_id={data.form_id}",
        )

        response = DeclineConsentResponse(
            logged=True,
            audit_id=audit_entry.id,
        )
        return response.model_dump()

    async def get_receipt(
        self, consent_id: str, requester_id: str, requester_role: str
    ) -> dict[str, Any]:
        """
        Get consent receipt.

        Args:
            consent_id: Consent ID.
            requester_id: ID of requester.
            requester_role: Role of requester.

        Returns:
            Receipt data.

        Raises:
            ValueError: If consent not found or unauthorized.
        """
        consent = await self.repo.get_by_id(consent_id)
        if not consent:
            raise ValueError("RESOURCE_NOT_FOUND")

        allow_access = (
            requester_role in ("super_admin", "org_admin")
            or requester_id == consent.user_id
        )
        if not allow_access:
            raise ValueError("INSUFFICIENT_SCOPE")

        if not consent.receipt_token:
            raise ValueError("RECEIPT_NOT_AVAILABLE")

        return {
            "consent_id": consent.id,
            "user_id": consent.user_id,
            "form_id": consent.form_id,
            "version": consent.version,
            "status": consent.status,
            "granted_at": consent.granted_at,
            "expires_at": consent.expires_at,
            "receipt_token": consent.receipt_token,
            "channel": consent.channel,
        }

    # ------------------------------------------------------------------
    # Public / inter-service methods (called by external microservices)
    # ------------------------------------------------------------------

    async def _ensure_shadow_user(self, external_user_id: str) -> None:
        """Upsert a minimal shadow record so the consent FK is satisfied.

        External users live in a different microservice.  We store a thin
        placeholder in dpdp_users keyed on their UUID so that the FK on
        dpdp_consents.user_id stays intact.  Shadow records cannot log in
        to this service (sentinel password_hash).
        """
        existing = await self.session.get(DpdpUser, external_user_id)
        if existing:
            return

        shadow = DpdpUser(
            id=external_user_id,
            role="citizen",
            name="External User",
            name_hash=sha256_hash(external_user_id),
            # Synthetic email that is clearly non-real and unique per UUID.
            email=f"__ext__{external_user_id}",
            email_hash=sha256_hash(f"external_shadow:{external_user_id}"),
            password_hash="EXTERNAL_USER_NO_AUTH",
            is_active="1",
        )
        self.session.add(shadow)
        await self.session.flush()

    async def public_grant_consent(
        self,
        data: PublicGrantConsentRequest,
        channel: str = "web",
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Accept consent on behalf of an external-service user.

        Args:
            data: Public grant request carrying the external user UUID.
            channel: Derived from the HTTP request (web/mobile).
            user_agent: Extracted from the User-Agent request header.
            ip_address: Extracted from the client IP / X-Forwarded-For header.

        Returns:
            ConsentGrantResponse dictionary with receipt_token.

        Raises:
            ValueError: CONSENT_ALREADY_GRANTED | FORM_VERSION_NOT_FOUND
        """
        await self._ensure_shadow_user(data.external_user_id)

        grant_request = GrantConsentRequest(
            user_id=data.external_user_id,
            form_id=data.form_id,
            version=data.version,
            optional_fields=data.optional_fields,
            channel=channel,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        result = await self.grant_consent(
            grant_request, actor_id=data.external_user_id
        )

        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == data.form_id)
        )
        if form:
            await self._fire_consent_webhook(
                org_id=form.org_id,
                event_type="consent.accepted",
                consent_id=result["id"],
                external_user_id=data.external_user_id,
                form_id=data.form_id,
                version=data.version,
                granted_at=result["granted_at"],
                expires_at=result["expires_at"],
            )

        return result

    async def public_accept_or_reconsent(
        self,
        data: PublicGrantConsentRequest,
        channel: str = "web",
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Grant consent or automatically re-consent if the user has an older version.

        Behaviour:
        - No existing consent → fresh grant (reconsented=False)
        - Existing consent, same active version → raises CONSENT_ALREADY_GRANTED
        - Existing consent, older version → supersedes it and grants the new
          version (reconsented=True, previous_consent_id set)

        Args:
            data: Public grant request carrying external_user_id and form details.
            channel: Derived from the HTTP request (web/mobile/api).
            user_agent: Extracted from the User-Agent request header.
            ip_address: Extracted from the client IP / X-Forwarded-For header.

        Returns:
            ConsentGrantResponse dict with reconsented flag and optional
            previous_consent_id.

        Raises:
            ValueError: CONSENT_ALREADY_GRANTED | FORM_VERSION_NOT_FOUND
        """
        await self._ensure_shadow_user(data.external_user_id)

        existing = await self.repo.get_active_consent(data.external_user_id, data.form_id)
        previous_consent_id: str | None = None

        if existing:
            if existing.version == data.version:
                raise ValueError("CONSENT_ALREADY_GRANTED")

            # Older version active — supersede it before granting the new one.
            previous_consent_id = existing.id
            await self.repo.update_by_id(
                existing.id,
                status=ConsentStatus.SUPERSEDED.value,
            )
            await write_audit_entry(
                self.session,
                actor=data.external_user_id,
                actor_type="user",
                action=AuditAction.CONSENT_SUPERSEDED.value,
                target=data.external_user_id,
                version=existing.version,
                details=(
                    f"form_id={data.form_id}, "
                    f"superseded_by_version={data.version}"
                ),
            )

        grant_request = GrantConsentRequest(
            user_id=data.external_user_id,
            form_id=data.form_id,
            version=data.version,
            optional_fields=data.optional_fields,
            channel=channel,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        result = await self.grant_consent(grant_request, actor_id=data.external_user_id)

        result["reconsented"] = previous_consent_id is not None
        result["previous_consent_id"] = previous_consent_id

        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == data.form_id)
        )
        if form:
            event_type = "consent.reconsented" if previous_consent_id else "consent.accepted"
            await self._fire_consent_webhook(
                org_id=form.org_id,
                event_type=event_type,
                consent_id=result["id"],
                external_user_id=data.external_user_id,
                form_id=data.form_id,
                version=data.version,
                granted_at=result["granted_at"],
                expires_at=result["expires_at"],
                previous_consent_id=previous_consent_id,
            )

        return result

    async def public_reconsent(self, data: ReconsentRequest) -> dict[str, Any]:
        """Re-consent: supersede the current consent and grant the new version.

        Marks any existing granted consent on the form as 'superseded', then
        creates a fresh consent record for new_version.

        Args:
            data: Reconsent request with external_user_id and new_version.

        Returns:
            Dictionary with previous_consent_id, new_consent_id, receipt_token, etc.

        Raises:
            ValueError: FORM_VERSION_NOT_FOUND | CONSENT_ALREADY_GRANTED
        """
        await self._ensure_shadow_user(data.external_user_id)

        old_consent = await self.repo.get_active_consent(
            data.external_user_id, data.form_id
        )
        previous_consent_id = None

        if old_consent:
            previous_consent_id = old_consent.id
            await self.repo.update_by_id(
                old_consent.id,
                status=ConsentStatus.SUPERSEDED.value,
            )
            await write_audit_entry(
                self.session,
                actor=data.external_user_id,
                actor_type="user",
                action=AuditAction.CONSENT_SUPERSEDED.value,
                target=data.external_user_id,
                version=old_consent.version,
                details=(
                    f"form_id={data.form_id}, "
                    f"superseded_by_version={data.new_version}"
                ),
            )

        grant_request = GrantConsentRequest(
            user_id=data.external_user_id,
            form_id=data.form_id,
            version=data.new_version,
            optional_fields=data.optional_fields,
            channel=data.channel,
            user_agent=data.user_agent,
            ip_address=data.ip_address,
        )
        new_grant = await self.grant_consent(
            grant_request, actor_id=data.external_user_id
        )

        form = await self.session.scalar(
            select(ConsentForm).where(ConsentForm.id == data.form_id)
        )
        if form:
            await self._fire_consent_webhook(
                org_id=form.org_id,
                event_type="consent.reconsented",
                consent_id=new_grant["id"],
                external_user_id=data.external_user_id,
                form_id=data.form_id,
                version=data.new_version,
                granted_at=new_grant["granted_at"],
                expires_at=new_grant["expires_at"],
                previous_consent_id=previous_consent_id,
            )

        return {
            **new_grant,
            "new_consent_id": new_grant["id"],
            "previous_consent_id": previous_consent_id,
        }

    async def get_public_form_details(self, form_id: str) -> dict[str, Any]:
        """Return the active form version content for frontend display.

        Args:
            form_id: UUID of the consent form.

        Returns:
            Form details including data_fields, purpose, user_rights, etc.

        Raises:
            ValueError: FORM_NOT_FOUND | FORM_NOT_ACTIVE
        """
        form = await self.session.get(ConsentForm, form_id)
        if not form:
            raise ValueError("FORM_NOT_FOUND")
        if form.status != "active":
            raise ValueError("FORM_NOT_ACTIVE")

        active_ver = None
        if form.active_version:
            active_ver = await self.session.scalar(
                select(FormVersion).where(
                    and_(
                        FormVersion.form_id == form_id,
                        FormVersion.version == form.active_version,
                    )
                )
            )

        return {
            "form_id": form.id,
            "name": form.name,
            "code": form.code,
            "purpose": form.purpose,
            "purpose_short": form.purpose_short,
            "description": form.description,
            "legal_basis": form.legal_basis,
            "active_version": form.active_version,
            "data_fields": active_ver.data_fields if active_ver else form.data_fields,
            "third_parties": active_ver.third_parties if active_ver else form.third_parties,
            "user_rights": active_ver.user_rights if active_ver else form.user_rights,
            "retention_days": int(active_ver.retention_days) if active_ver else int(form.retention_days or 0),
            "expiry_days": int(active_ver.expiry_days) if active_ver else int(form.expiry_days or 0),
            "version_title": active_ver.title if active_ver else None,
            "version_description": active_ver.description if active_ver else None,
            "custom_body": active_ver.custom_body if active_ver else None,
        }

    async def _fire_consent_webhook(
        self,
        org_id: str,
        event_type: str,
        consent_id: str,
        external_user_id: str,
        form_id: str,
        version: str,
        granted_at: datetime,
        expires_at: datetime,
        previous_consent_id: Optional[str] = None,
    ) -> None:
        """Fire a consent event webhook to the organization's webhook URL.

        Fires as fire-and-forget async task. Failures do not affect the
        consent operation.

        Args:
            org_id: Organization ID.
            event_type: Type of event (consent.accepted, consent.reconsented).
            consent_id: ID of the newly created consent.
            external_user_id: External user UUID.
            form_id: Form ID.
            version: Consent version.
            granted_at: When consent was granted.
            expires_at: When consent expires.
            previous_consent_id: Previous consent ID (for reconsent).
        """
        asyncio.create_task(
            self._send_webhook_event(
                org_id=org_id,
                event_type=event_type,
                consent_id=consent_id,
                external_user_id=external_user_id,
                form_id=form_id,
                version=version,
                granted_at=granted_at,
                expires_at=expires_at,
                previous_consent_id=previous_consent_id,
            )
        )

    async def _send_webhook_event(
        self,
        org_id: str,
        event_type: str,
        consent_id: str,
        external_user_id: str,
        form_id: str,
        version: str,
        granted_at: datetime,
        expires_at: datetime,
        previous_consent_id: Optional[str] = None,
    ) -> None:
        """Send webhook event to organization webhook URL.

        Args:
            org_id: Organization ID.
            event_type: Type of event.
            consent_id: Consent ID.
            external_user_id: External user UUID.
            form_id: Form ID.
            version: Consent version.
            granted_at: When consent was granted.
            expires_at: When consent expires.
            previous_consent_id: Previous consent ID if applicable.
        """
        if not httpx:
            return

        try:
            org = await self.session.scalar(
                select(Org).where(Org.id == org_id)
            )
            if not org or not org.webhook_url:
                return

            payload = {
                "event": event_type,
                "consent_id": consent_id,
                "external_user_id": external_user_id,
                "form_id": form_id,
                "version": version,
                "status": "granted",
                "granted_at": granted_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
            if previous_consent_id:
                payload["previous_consent_id"] = previous_consent_id

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    org.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
        except Exception:
            pass
