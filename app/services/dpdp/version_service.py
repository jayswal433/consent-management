from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.audit_writer import write_audit_entry
from app.models.orm.form_version import FormVersion
from app.models.orm.consent_form import ConsentForm
from app.repositories.form_repository import FormRepository
from app.repositories.version_repository import VersionRepository
from app.schemas.dpdp.version import (
    CreateVersionRequest,
    PublishVersionRequest,
    RollbackVersionRequest,
    SubmitVersionRequest,
    UpdateVersionRequest,
)


class VersionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.version_repo = VersionRepository(session)
        self.form_repo = FormRepository(session)

    async def list_versions(self, form_id: str) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        versions = await self.version_repo.list_versions(form_id)

        items = [
            {
                "id": v.id,
                "form_id": v.form_id,
                "version": v.version,
                "status": v.status,
                "title": v.title,
                "purpose": v.purpose,
                "legal_basis": v.legal_basis,
                "retention_days": int(v.retention_days),
                "expiry_days": int(v.expiry_days),
                "published_at": v.published_at,
                "published_by": v.published_by,
                "created_at": v.created_at,
            }
            for v in versions
        ]

        return {
            "form_id": form_id,
            "versions": items,
            "total": len(items),
        }

    async def create_version(
        self,
        form_id: str,
        data: CreateVersionRequest,
        actor_id: str,
    ) -> dict:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return {
                "error": "FORM_NOT_FOUND",
                "message": f"Form {form_id} not found",
                "status_code": 404,
            }

        draft_version = await self.version_repo.get_draft_version(form_id)
        if draft_version:
            return {
                "error": "VERSION_DRAFT_EXISTS",
                "message": "A draft version already exists for this form",
                "status_code": 409,
            }

        next_version = await self.version_repo.get_next_version_string(form_id)

        version = await self.version_repo.create(
            form_id=form_id,
            version=next_version,
            status="draft",
            title=data.title,
            description=data.description,
            purpose=data.purpose,
            legal_basis=data.legal_basis,
            retention_days=str(data.retention_days),
            expiry_days=str(data.expiry_days),
            third_parties=data.third_parties,
            user_rights=data.user_rights,
            data_fields=data.data_fields,
            custom_body=data.custom_body,
            reviewer_note=data.reviewer_note,
        )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="version_created",
            target=form_id,
            version=next_version,
            org_id=form.org_id,
            details=f"Version {next_version} created",
        )

        await self.session.commit()

        return {
            "id": version.id,
            "form_id": version.form_id,
            "version": version.version,
            "status": version.status,
            "created_at": version.created_at,
        }

    async def update_version(
        self,
        form_id: str,
        version: str,
        data: UpdateVersionRequest,
        actor_id: str,
    ) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        version_obj = await self.version_repo.get_by_form_and_version(
            form_id, version
        )
        if not version_obj:
            return None

        if version_obj.status not in ("draft",):
            return {
                "error": "CANNOT_EDIT_VERSION",
                "message": (
                    "Can only edit versions in draft status"
                ),
                "status_code": 403,
            }

        update_data = {}
        if data.title is not None:
            update_data["title"] = data.title
        if data.description is not None:
            update_data["description"] = data.description
        if data.purpose is not None:
            update_data["purpose"] = data.purpose
        if data.legal_basis is not None:
            update_data["legal_basis"] = data.legal_basis
        if data.retention_days is not None:
            update_data["retention_days"] = str(data.retention_days)
        if data.expiry_days is not None:
            update_data["expiry_days"] = str(data.expiry_days)
        if data.third_parties is not None:
            update_data["third_parties"] = data.third_parties
        if data.user_rights is not None:
            update_data["user_rights"] = data.user_rights
        if data.data_fields is not None:
            update_data["data_fields"] = data.data_fields
        if data.custom_body is not None:
            update_data["custom_body"] = data.custom_body

        if update_data:
            updated = await self.version_repo.update_by_id(
                version_obj.id, **update_data
            )

            await write_audit_entry(
                session=self.session,
                actor=actor_id,
                actor_type="admin",
                action="version_updated",
                target=form_id,
                version=version,
                org_id=form.org_id,
                details=f"Version {version} updated",
            )

            await self.session.commit()

        return await self._get_version(form_id, version)

    async def submit_version(
        self,
        form_id: str,
        version: str,
        data: SubmitVersionRequest,
        actor_id: str,
    ) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        version_obj = await self.version_repo.get_by_form_and_version(
            form_id, version
        )
        if not version_obj:
            return None

        if version_obj.status == "in_review":
            return {
                "error": "VERSION_ALREADY_IN_REVIEW",
                "message": "This version is already under review",
                "status_code": 409,
            }

        if version_obj.status != "draft":
            return {
                "error": "INVALID_VERSION_STATUS",
                "message": "Only draft versions can be submitted for review",
                "status_code": 403,
            }

        updated = await self.version_repo.update_by_id(
            version_obj.id,
            status="in_review",
            submitted_at=datetime.now(UTC),
            reviewer_note=data.reviewer_note,
        )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="version_submitted",
            target=form_id,
            version=version,
            org_id=form.org_id,
            details=f"Version {version} submitted for review",
        )

        await self.session.commit()

        return await self._get_version(form_id, version)

    async def publish_version(
        self,
        form_id: str,
        version: str,
        data: PublishVersionRequest,
        actor_id: str,
    ) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        version_obj = await self.version_repo.get_by_form_and_version(
            form_id, version
        )
        if not version_obj:
            return None

        if version_obj.status != "in_review":
            return {
                "error": "PUBLISH_NOT_IN_REVIEW",
                "message": "Only in_review versions can be published",
                "status_code": 422,
            }

        active_version = await self.version_repo.get_active_version(form_id)
        if active_version:
            await self.version_repo.update_by_id(
                active_version.id,
                status="archived",
                archived_at=datetime.now(UTC),
            )

        now = datetime.now(UTC)
        updated = await self.version_repo.update_by_id(
            version_obj.id,
            status="active",
            published_at=now,
            published_by=data.reviewer_sign_off,
            review_note=data.review_note,
        )

        await self.form_repo.update_by_id(
            form_id,
            active_version=version,
            status="active",
        )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="version_published",
            target=form_id,
            version=version,
            org_id=form.org_id,
            details=f"Version {version} published by {data.reviewer_sign_off}",
        )

        await self.session.commit()

        return await self._get_version(form_id, version)

    async def rollback_version(
        self,
        form_id: str,
        version: str,
        data: RollbackVersionRequest,
        actor_id: str,
    ) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        version_obj = await self.version_repo.get_by_form_and_version(
            form_id, version
        )
        if not version_obj:
            return None

        if version_obj.status != "active":
            return {
                "error": "INVALID_VERSION_STATUS",
                "message": "Can only rollback active versions",
                "status_code": 403,
            }

        active_version = await self.version_repo.get_active_version(form_id)
        if active_version:
            await self.version_repo.update_by_id(
                active_version.id,
                status="archived",
                archived_at=datetime.now(UTC),
            )

        archived_result = await self.session.execute(
            select(FormVersion)
            .where(
                and_(
                    FormVersion.form_id == form_id,
                    FormVersion.status == "archived",
                )
            )
            .order_by(desc(FormVersion.published_at))
            .limit(1)
        )
        archived_version = archived_result.scalar_one_or_none()

        if archived_version:
            await self.version_repo.update_by_id(
                archived_version.id,
                status="active",
            )

            await self.form_repo.update_by_id(
                form_id,
                active_version=archived_version.version,
            )

        await write_audit_entry(
            session=self.session,
            actor=actor_id,
            actor_type="admin",
            action="version_rollback",
            target=form_id,
            version=version,
            org_id=form.org_id,
            details=f"Version {version} rolled back. Reason: {data.reason}",
        )

        await self.session.commit()

        return {"form_id": form_id, "rolled_back_version": version}

    async def get_version_diff(
        self,
        form_id: str,
        from_version: str,
        to_version: str,
    ) -> dict | None:
        form = await self.form_repo.get_by_id(form_id)
        if not form:
            return None

        from_ver = await self.version_repo.get_by_form_and_version(
            form_id, from_version
        )
        if not from_ver:
            return None

        to_ver = await self.version_repo.get_by_form_and_version(
            form_id, to_version
        )
        if not to_ver:
            return None

        from_fields = from_ver.data_fields or []
        to_fields = to_ver.data_fields or []

        from_field_names = {f["name"]: f for f in from_fields}
        to_field_names = {f["name"]: f for f in to_fields}

        added = []
        for name, field in to_field_names.items():
            if name not in from_field_names:
                added.append(field)

        removed = []
        for name, field in from_field_names.items():
            if name not in to_field_names:
                removed.append(field)

        changed = []
        for name, to_field in to_field_names.items():
            if name in from_field_names:
                from_field = from_field_names[name]
                if from_field != to_field:
                    changed.append(
                        {
                            "field": name,
                            "from_value": from_field,
                            "to_value": to_field,
                        }
                    )

        return {
            "from_version": from_version,
            "to_version": to_version,
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    async def _get_version(self, form_id: str, version: str) -> dict | None:
        version_obj = await self.version_repo.get_by_form_and_version(
            form_id, version
        )
        if not version_obj:
            return None

        return {
            "id": version_obj.id,
            "form_id": version_obj.form_id,
            "version": version_obj.version,
            "status": version_obj.status,
            "title": version_obj.title,
            "purpose": version_obj.purpose,
            "legal_basis": version_obj.legal_basis,
            "retention_days": int(version_obj.retention_days),
            "expiry_days": int(version_obj.expiry_days),
            "data_fields": version_obj.data_fields,
            "published_at": version_obj.published_at,
            "published_by": version_obj.published_by,
            "created_at": version_obj.created_at,
        }
