from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.core.security.audit_writer import write_audit_entry
from app.core.security.crypto import decrypt_field, encrypt_field, get_dek, sha256_hash
from app.models.orm.dpdp_enums import ActorType, AuditAction
from app.models.orm.org import Org
from app.repositories.org_repository import OrgRepository
from app.schemas.dpdp.org import OrgCreateRequest, OrgResponse, OrgUpdateRequest


class OrgService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrgRepository(session)

    async def get_org(self, org_id: str) -> dict[str, Any]:
        org = await self.repo.get_by_id(org_id)
        if not org:
            return StandardResponse.not_found(
                message="Organization not found",
                data={"error": "ORG_NOT_FOUND"},
            ).make

        response = self._serialize_org(org, decrypt=True)
        return StandardResponse.success(
            data=response, message="Organization retrieved successfully"
        ).make

    async def list_orgs(self, page: int = 1, limit: int = 20) -> dict[str, Any]:
        if page < 1 or limit < 1:
            return StandardResponse.bad_request(
                message="Invalid pagination parameters",
                data={"error": "INVALID_PAGINATION"},
            ).make

        orgs, total = await self.repo.list_orgs(page, limit)

        serialized_orgs = [
            self._serialize_org(org, decrypt=False) for org in orgs
        ]

        return StandardResponse.success(
            data={
                "items": serialized_orgs,
                "total": total,
                "page": page,
                "limit": limit,
            },
            message="Organizations retrieved successfully",
        ).make

    async def create_org(
        self, data: OrgCreateRequest, actor_id: str
    ) -> dict[str, Any]:
        existing_by_name = await self.repo.get_by_name(data.name)
        if existing_by_name:
            return StandardResponse.conflict(
                message="Organization name already exists",
                data={"error": "DUPLICATE_ORG_NAME"},
            ).make

        short_code_upper = data.short_code.upper()
        existing_by_code = await self.repo.get_by_short_code(short_code_upper)
        if existing_by_code:
            return StandardResponse.conflict(
                message="Organization short code already exists",
                data={"error": "DUPLICATE_ORG_CODE"},
            ).make

        dek = get_dek()
        dpo_name_encrypted = encrypt_field(data.dpo_name, dek)
        dpo_email_encrypted = encrypt_field(data.dpo_email, dek)
        dpo_email_hash = sha256_hash(data.dpo_email.lower())

        org = await self.repo.create(
            name=data.name,
            short_code=short_code_upper,
            color=data.color,
            role=data.role,
            plan=data.plan,
            dpo_name=dpo_name_encrypted,
            dpo_email=dpo_email_encrypted,
            dpo_email_hash=dpo_email_hash,
            dpdp_reg_id=data.dpdp_reg_id,
            status="active",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await write_audit_entry(
            self.session,
            actor=actor_id,
            actor_type=ActorType.ADMIN.value,
            action=AuditAction.ORG_CREATED.value,
            target=org.id,
            org_id=org.id,
        )

        await self.session.commit()

        response = self._serialize_org(org, decrypt=True)
        return StandardResponse.created(
            data=response, message="Organization created successfully"
        ).make

    async def update_org(
        self, org_id: str, data: OrgUpdateRequest, actor_id: str
    ) -> dict[str, Any]:
        org = await self.repo.get_by_id(org_id)
        if not org:
            return StandardResponse.not_found(
                message="Organization not found",
                data={"error": "ORG_NOT_FOUND"},
            ).make

        update_fields = {}

        if data.name is not None:
            if data.name != org.name:
                existing = await self.repo.get_by_name(data.name)
                if existing:
                    return StandardResponse.conflict(
                        message="Organization name already exists",
                        data={"error": "DUPLICATE_ORG_NAME"},
                    ).make
            update_fields["name"] = data.name

        if data.dpo_name is not None:
            dek = get_dek()
            update_fields["dpo_name"] = encrypt_field(data.dpo_name, dek)

        if data.dpo_email is not None:
            dek = get_dek()
            update_fields["dpo_email"] = encrypt_field(data.dpo_email, dek)
            update_fields["dpo_email_hash"] = sha256_hash(
                data.dpo_email.lower()
            )

        if data.plan is not None:
            update_fields["plan"] = data.plan

        if data.color is not None:
            update_fields["color"] = data.color

        if update_fields:
            update_fields["updated_at"] = datetime.now(UTC)
            updated_org = await self.repo.update_by_id(org_id, **update_fields)

            await write_audit_entry(
                self.session,
                actor=actor_id,
                actor_type=ActorType.ADMIN.value,
                action=AuditAction.ORG_CREATED.value,
                target=org_id,
                details=str(list(update_fields.keys())),
                org_id=org_id,
            )

            await self.session.commit()
        else:
            updated_org = org

        response = self._serialize_org(updated_org, decrypt=True)
        return StandardResponse.success(
            data=response, message="Organization updated successfully"
        ).make

    def _serialize_org(self, org: Org, decrypt: bool = False) -> dict[str, Any]:
        dpo_name = None
        dpo_email = None

        if decrypt and org.dpo_name and org.dpo_email:
            try:
                dek = get_dek()
                dpo_name = decrypt_field(org.dpo_name, dek)
                dpo_email = decrypt_field(org.dpo_email, dek)
            except Exception:
                dpo_name = None
                dpo_email = None

        return {
            "id": org.id,
            "name": org.name,
            "short_code": org.short_code,
            "color": org.color,
            "role": org.role,
            "plan": org.plan,
            "dpo_name": dpo_name,
            "dpo_email": dpo_email,
            "dpdp_reg_id": org.dpdp_reg_id,
            "status": org.status,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
        }
