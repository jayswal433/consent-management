from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.consent_form import ConsentForm
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.form_version import FormVersion
from app.repositories.base import BaseRepository


class FormRepository(BaseRepository[ConsentForm]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ConsentForm, session)

    async def get_by_code(self, code: str) -> ConsentForm | None:
        result = await self.session.execute(
            select(ConsentForm).where(ConsentForm.code == code)
        )
        return result.scalar_one_or_none()

    async def list_forms(
        self,
        status: str | None = None,
        owner: str | None = None,
        q: str | None = None,
        sort_by: str = "created_at",
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ConsentForm], int]:
        conditions = []
        if status:
            conditions.append(ConsentForm.status == status)
        if owner:
            conditions.append(ConsentForm.owner == owner)
        if q:
            conditions.append(
                (ConsentForm.name.ilike(f"%{q}%"))
                | (ConsentForm.code.ilike(f"%{q}%"))
            )

        stmt = select(ConsentForm)
        if conditions:
            stmt = stmt.where(*conditions)

        total_result = await self.session.execute(
            select(func.count()).select_from(ConsentForm).where(*conditions)
            if conditions
            else select(func.count()).select_from(ConsentForm)
        )
        total = total_result.scalar_one()

        if sort_by == "created_at":
            stmt = stmt.order_by(ConsentForm.created_at.desc())
        elif sort_by == "name":
            stmt = stmt.order_by(ConsentForm.name.asc())
        elif sort_by == "status":
            stmt = stmt.order_by(ConsentForm.status.asc())
        else:
            stmt = stmt.order_by(ConsentForm.created_at.desc())

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        forms = result.scalars().all()

        return forms, total

    async def get_published_forms_by_org(
        self, org_id: str
    ) -> list[tuple[ConsentForm, FormVersion | None]]:
        result = await self.session.execute(
            select(ConsentForm, FormVersion)
            .outerjoin(
                FormVersion,
                and_(
                    FormVersion.form_id == ConsentForm.id,
                    FormVersion.status == "active",
                ),
            )
            .where(
                and_(
                    ConsentForm.org_id == org_id,
                    ConsentForm.status == "active",
                )
            )
            .order_by(ConsentForm.created_at.desc())
        )
        return result.all()

    async def get_latest_published_form_by_org(
        self, org_id: str
    ) -> tuple[ConsentForm, FormVersion | None] | None:
        result = await self.session.execute(
            select(ConsentForm, FormVersion)
            .outerjoin(
                FormVersion,
                and_(
                    FormVersion.form_id == ConsentForm.id,
                    FormVersion.status == "active",
                ),
            )
            .where(
                and_(
                    ConsentForm.org_id == org_id,
                    ConsentForm.status == "active",
                )
            )
            .order_by(FormVersion.published_at.desc())
            .limit(1)
        )
        return result.one_or_none()

    async def has_active_consents(self, form_id: str) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                (DpdpConsent.form_id == form_id)
                & (DpdpConsent.status == "granted")
            )
        )
        count = result.scalar_one()
        return count > 0
