from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.core.security.audit_writer import write_audit_entry
from app.core.security.crypto import decrypt_field, encrypt_field, get_dek, sha256_hash
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import ActorType, AuditAction
from app.models.orm.dpdp_user import DpdpUser
from app.models.orm.nomination import Nomination
from app.repositories.dpdp_user_repository import DpdpUserRepository
from app.repositories.org_repository import OrgRepository
from app.schemas.dpdp.user import (
    DpdpUserCreateRequest,
    ErasureRequest,
    NomineeCreateRequest,
    PortabilityRequest,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DpdpUserRepository(session)

    async def get_user(
        self, user_id: str, requester_id: str, requester_role: str
    ) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        is_self = requester_id == user_id
        can_decrypt = is_self or requester_role == "super_admin"

        response = self._serialize_user(user, decrypt=can_decrypt)
        return StandardResponse.success(
            data=response, message="User retrieved successfully"
        ).make

    async def list_users(
        self, org_id: str | None, page: int = 1, limit: int = 20
    ) -> dict[str, Any]:
        if page < 1 or limit < 1:
            return StandardResponse.bad_request(
                message="Invalid pagination parameters",
                data={"error": "INVALID_PAGINATION"},
            ).make

        users, total = await self.repo.list_users(org_id, page, limit)

        serialized_users = [self._serialize_user(user, decrypt=False) for user in users]

        return StandardResponse.success(
            data={
                "items": serialized_users,
                "total": total,
                "page": page,
                "limit": limit,
            },
            message="Users retrieved successfully",
        ).make

    async def get_user_consents(
        self, user_id: str, status_filter: str | None = None
    ) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        query = select(DpdpConsent).where(DpdpConsent.user_id == user_id)

        if status_filter:
            query = query.where(DpdpConsent.status == status_filter)

        result = await self.session.execute(query)
        consents = result.scalars().all()

        consent_items = [
            {
                "form_id": c.form_id,
                "version": c.version,
                "status": c.status,
                "granted_at": c.granted_at,
                "expires_at": c.expires_at,
            }
            for c in consents
        ]

        return StandardResponse.success(
            data={"consents": consent_items, "total": len(consents)},
            message="User consents retrieved successfully",
        ).make

    async def get_user_rights(self, user_id: str) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        rights = [
            "withdraw",
            "access",
            "delete",
            "portability",
            "nominate",
        ]

        return StandardResponse.success(
            data={"rights": rights}, message="User rights retrieved successfully"
        ).make

    async def erasure(
        self, user_id: str, data: ErasureRequest, actor_id: str
    ) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        consents_result = await self.session.execute(
            select(DpdpConsent).where(DpdpConsent.user_id == user_id)
        )
        consents = consents_result.scalars().all()

        for consent in consents:
            consent.status = "withdrawn"
            consent.withdrawn_at = datetime.now(UTC)
            consent.updated_at = datetime.now(UTC)

        user.name = None
        user.email = None
        user.phone = None
        user.initials = None
        user.name_hash = sha256_hash("")
        user.email_hash = sha256_hash("")
        user.phone_hash = None
        user.is_active = "0"
        user.updated_at = datetime.now(UTC)

        erasure_receipt_id = str(uuid.uuid4())

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.USER.value if actor_id == user_id else ActorType.ADMIN.value,
            action=AuditAction.PII_ERASURE.value,
            target=user_id,
            details=f"Reason: {data.reason}",
            org_id=user.org_id,
        )

        self.session.add(user)
        for consent in consents:
            self.session.add(consent)

        await self.session.commit()

        return StandardResponse.success(
            data={
                "deleted": True,
                "affected_consents": len(consents),
                "erasure_receipt_id": erasure_receipt_id,
            },
            message="User data erased successfully",
        ).make

    async def portability(
        self, user_id: str, data: PortabilityRequest, actor_id: str
    ) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        consents_result = await self.session.execute(
            select(DpdpConsent).where(DpdpConsent.user_id == user_id)
        )
        consents = consents_result.scalars().all()

        export_id = str(uuid.uuid4())
        download_url = f"/v1/users/{user_id}/data/export/{export_id}"

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.USER.value if actor_id == user_id else ActorType.ADMIN.value,
            action=AuditAction.EXPORT_REQUESTED.value,
            target=user_id,
            details=f"Format: {data.format}, Export ID: {export_id}",
            org_id=user.org_id,
        )

        await self.session.commit()

        return StandardResponse.success(
            data={
                "download_url": download_url,
                "export_id": export_id,
            },
            message="Data export initiated successfully",
        ).make

    async def register_nominee(
        self, user_id: str, data: NomineeCreateRequest, actor_id: str
    ) -> dict[str, Any]:
        user = await self.repo.get_by_id(user_id)
        if not user:
            return StandardResponse.not_found(
                message="User not found", data={"error": "USER_NOT_FOUND"}
            ).make

        dek = get_dek()
        nominee_name_encrypted = encrypt_field(data.nominee_name, dek)
        nominee_email_encrypted = encrypt_field(data.nominee_email, dek)
        nominee_email_hash = sha256_hash(data.nominee_email.lower())

        nominee_phone_encrypted = None
        nominee_phone_hash = None
        if data.nominee_phone:
            nominee_phone_encrypted = encrypt_field(data.nominee_phone, dek)
            nominee_phone_hash = sha256_hash(data.nominee_phone)

        nomination = Nomination(
            id=str(uuid.uuid4()),
            user_id=user_id,
            nominee_name=nominee_name_encrypted,
            nominee_email=nominee_email_encrypted,
            nominee_email_hash=nominee_email_hash,
            nominee_phone=nominee_phone_encrypted,
            nominee_phone_hash=nominee_phone_hash,
            is_active="1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        self.session.add(nomination)

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.USER.value,
            action=AuditAction.ORG_CREATED.value,
            target=user_id,
            details=f"Nominee registered: {nominee_email_hash[:8]}...",
            org_id=user.org_id,
        )

        await self.session.commit()

        return StandardResponse.created(
            data={
                "nominee_id": nomination.id,
                "created_at": nomination.created_at,
            },
            message="Nominee registered successfully",
        ).make

    async def create_user(self, data: DpdpUserCreateRequest) -> dict[str, Any]:
        if data.org_id is not None:
            org = await OrgRepository(self.session).get_by_id(data.org_id)
            if not org:
                return StandardResponse.not_found(
                    message="Organisation not found",
                    data={"error": "ORG_NOT_FOUND"},
                ).make

        existing_user = await self.repo.get_by_email_hash(
            sha256_hash(data.email.lower())
        )
        if existing_user:
            return StandardResponse.conflict(
                message="Email already registered",
                data={"error": "DUPLICATE_EMAIL"},
            ).make

        dek = get_dek()
        name_encrypted = encrypt_field(data.name, dek)
        name_hash = sha256_hash(data.name.lower())

        email_encrypted = encrypt_field(data.email, dek)
        email_hash = sha256_hash(data.email.lower())

        phone_encrypted = None
        phone_hash = None
        if data.phone:
            phone_encrypted = encrypt_field(data.phone, dek)
            phone_hash = sha256_hash(data.phone)

        password_hash = pwd_context.hash(data.password)

        user = await self.repo.create(
            org_id=data.org_id,
            role=data.role,
            name=name_encrypted,
            name_hash=name_hash,
            email=email_encrypted,
            email_hash=email_hash,
            phone=phone_encrypted,
            phone_hash=phone_hash,
            password_hash=password_hash,
            is_active="1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await self.session.commit()

        response = self._serialize_user(user, decrypt=True)
        return StandardResponse.created(
            data=response, message="User created successfully"
        ).make

    def _serialize_user(self, user: DpdpUser, decrypt: bool = False) -> dict[str, Any]:
        name = None
        email = None

        if decrypt:
            try:
                dek = get_dek()
                if user.name:
                    name = decrypt_field(user.name, dek)
                if user.email:
                    email = decrypt_field(user.email, dek)
            except Exception:
                name = None
                email = None

        return {
            "id": user.id,
            "org_id": user.org_id,
            "role": user.role,
            "name": name,
            "email": email,
            "created_at": user.created_at,
        }
