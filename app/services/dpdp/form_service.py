from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.audit_writer import write_audit_entry
from app.models.orm.consent_form import ConsentForm
from app.models.orm.dpdp_consent import DpdpConsent
from app.repositories.form_repository import FormRepository
from app.schemas.dpdp.form import (
    CreateFormRequest,
    DeactivateFormRequest,
    UpdateFormRequest,
)


class FormService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FormRepository(session)

    async def list_forms(
        self,
        status: str | None = None,
        owner: str | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        forms, total = await self.repo.list_forms(
            status=status,
            owner=owner,
            q=q,
            sort_by=sort_by,
            page=page,
            limit=limit,
        )

        items = []
        for form in forms:
            consent_count = await self._get_consent_count(form.id)
            items.append(
                {
                    "id": form.id,
                    "name": form.name,
                    "code": form.code,
                    "status": form.status,
                    "active_version": form.active_version,
                    "org_id": form.org_id,
                    "created_at": form.created_at,
                    "consent_count": consent_count,
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    async def create_form(
        self, data: CreateFormRequest, actor_id: str
    ) -> dict:
        existing = await self.repo.get_by_code(data.code.upper())
        if existing:
            return {
                "error": "DUPLICATE_FORM_CODE",
                "message": f"Form with code {data.code} already exists",
                "status_code": 409,
            }

        form = await self.repo.create(
            org_id=data.org_id,
            name=data.name,
            code=data.code.upper(),
            owner=data.owner,
            purpose_short=data.purpose_short,
            purpose=data.purpose,
            description=data.description,
            legal_basis=data.legal_basis,
            retention_days=str(data.retention_days),
            expiry_days=str(data.expiry_days),
            third_parties=data.third_parties,
            user_rights=data.user_rights,
            data_fields=data.data_fields,
            status="draft",
            active_version=None,
        )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="form_created",
            target=form.id,
            org_id=data.org_id,
            details=f"Form created: {form.name}",
        )

        await self.session.commit()

        return {
            "id": form.id,
            "code": form.code,
            "status": form.status,
            "created_at": form.created_at,
        }

    async def get_form(self, form_id: str) -> dict | None:
        form = await self.repo.get_by_id(form_id)
        if not form:
            return None

        versions_result = await self.session.execute(
            select(func.count())
            .select_from(ConsentForm)
            .where(ConsentForm.id == form_id)
        )
        from app.models.orm.form_version import FormVersion

        versions_result = await self.session.execute(
            select(FormVersion).where(FormVersion.form_id == form_id)
        )
        versions = versions_result.scalars().all()
        version_list = [
            {"id": v.id, "version": v.version, "status": v.status}
            for v in versions
        ]

        consent_count = await self._get_consent_count(form_id)

        return {
            "id": form.id,
            "name": form.name,
            "code": form.code,
            "org_id": form.org_id,
            "owner": form.owner,
            "status": form.status,
            "active_version": form.active_version,
            "purpose": form.purpose,
            "purpose_short": form.purpose_short,
            "description": form.description,
            "legal_basis": form.legal_basis,
            "retention_days": int(form.retention_days),
            "expiry_days": int(form.expiry_days),
            "third_parties": form.third_parties,
            "user_rights": form.user_rights,
            "data_fields": form.data_fields,
            "versions": version_list,
            "consent_count": consent_count,
            "created_at": form.created_at,
            "updated_at": form.updated_at,
        }

    async def update_form(
        self, form_id: str, data: UpdateFormRequest, actor_id: str
    ) -> dict | None:
        form = await self.repo.get_by_id(form_id)
        if not form:
            return None

        update_data = {}
        if data.owner is not None:
            update_data["owner"] = data.owner
        if data.purpose_short is not None:
            update_data["purpose_short"] = data.purpose_short

        if not update_data:
            return await self.get_form(form_id)

        updated_form = await self.repo.update_by_id(form_id, **update_data)

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="form_updated",
            target=form_id,
            org_id=form.org_id,
            details="Form details updated",
        )

        await self.session.commit()

        return await self.get_form(form_id)

    async def delete_form(self, form_id: str, actor_id: str) -> dict | None:
        form = await self.repo.get_by_id(form_id)
        if not form:
            return None

        if form.status != "draft":
            return {
                "error": "INVALID_FORM_STATUS",
                "message": "Form can only be deleted in draft status",
                "status_code": 403,
            }

        has_active = await self.repo.has_active_consents(form_id)
        if has_active:
            return {
                "error": "FORM_HAS_ACTIVE_CONSENTS",
                "message": (
                    "Cannot delete form with active consents. "
                    "Deactivate the form first."
                ),
                "status_code": 403,
            }

        await self.session.delete(form)
        await self.session.flush()

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="form_deleted",
            target=form_id,
            org_id=form.org_id,
            details="Form deleted",
        )

        await self.session.commit()

        return {"id": form_id, "deleted_at": datetime.now(UTC)}

    async def activate_form(self, form_id: str, actor_id: str) -> dict | None:
        form = await self.repo.get_by_id(form_id)
        if not form:
            return None

        if form.status == "draft" and not form.active_version:
            return {
                "error": "FORM_NEVER_PUBLISHED",
                "message": (
                    "Form must have been published at least once before activation"
                ),
                "status_code": 403,
            }

        if form.status == "active":
            return await self.get_form(form_id)

        updated_form = await self.repo.update_by_id(
            form_id, status="active"
        )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="form_activated",
            target=form_id,
            org_id=form.org_id,
            details="Form activated",
        )

        await self.session.commit()

        return await self.get_form(form_id)

    async def deactivate_form(
        self, form_id: str, data: DeactivateFormRequest, actor_id: str
    ) -> dict | None:
        form = await self.repo.get_by_id(form_id)
        if not form:
            return None

        if form.status == "deactivated":
            return await self.get_form(form_id)

        updated_form = await self.repo.update_by_id(
            form_id, status="deactivated"
        )

        details = f"Form deactivated. Reason: {data.reason}"
        if data.notify_dpo:
            details += " [DPO notified]"

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="form_deactivated",
            target=form_id,
            org_id=form.org_id,
            details=details,
        )

        await self.session.commit()

        return await self.get_form(form_id)

    async def get_published_forms_by_org(self, org_id: str) -> list[dict]:
        rows = await self.repo.get_published_forms_by_org(org_id)
        return [
            {
                "id": form.id,
                "name": form.name,
                "code": form.code,
                "status": form.status,
                "org_id": form.org_id,
                "active_version": form.active_version,
                "published_at": version.published_at if version else None,
                "published_by": version.published_by if version else None,
                "created_at": form.created_at,
            }
            for form, version in rows
        ]

    async def get_latest_published_form_by_org(self, org_id: str) -> dict | None:
        row = await self.repo.get_latest_published_form_by_org(org_id)
        if not row:
            return None
        form, version = row
        return {
            "id": form.id,
            "name": form.name,
            "code": form.code,
            "org_id": form.org_id,
            "owner": form.owner,
            "status": form.status,
            "active_version": form.active_version,
            "purpose_short": form.purpose_short,
            "created_at": form.created_at,
            "updated_at": form.updated_at,
            "version_id": version.id if version else None,
            "version": version.version if version else None,
            "title": version.title if version else None,
            "description": version.description if version else None,
            "purpose": version.purpose if version else None,
            "legal_basis": version.legal_basis if version else None,
            "retention_days": int(version.retention_days) if version and version.retention_days else None,
            "expiry_days": int(version.expiry_days) if version and version.expiry_days else None,
            "third_parties": version.third_parties if version else None,
            "user_rights": version.user_rights if version else None,
            "data_fields": version.data_fields if version else None,
            "custom_body": version.custom_body if version else None,
            "published_at": version.published_at if version else None,
            "published_by": version.published_by if version else None,
        }

    async def _get_consent_count(self, form_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                (DpdpConsent.form_id == form_id)
                & (DpdpConsent.status == "granted")
            )
        )
        return result.scalar_one()
