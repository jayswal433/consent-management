from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import StandardResponse
from app.models.orm.consent_form import ConsentForm
from app.models.orm.dpdp_consent import DpdpConsent
from app.models.orm.dpdp_enums import ConsentStatus, VersionStatus
from app.repositories.base import BaseRepository


class AnalyticsService:
    """Service for analytics and reporting operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_consent_trend(
        self,
        days: int = 30,
        form_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get consent trend data for the last N days.

        Args:
            days: Number of days to include
            form_id: Optional filter by form ID

        Returns:
            Standard response with trend data
        """
        since = datetime.now(UTC) - timedelta(days=days)

        filters_granted = [
            DpdpConsent.status == ConsentStatus.GRANTED.value,
            DpdpConsent.granted_at >= since
        ]
        filters_withdrawn = [
            DpdpConsent.status == ConsentStatus.WITHDRAWN.value,
            DpdpConsent.withdrawn_at >= since
        ]

        if form_id:
            filters_granted.append(DpdpConsent.form_id == form_id)
            filters_withdrawn.append(DpdpConsent.form_id == form_id)

        granted_stmt = (
            select(
                func.date(DpdpConsent.granted_at).label("date"),
                func.count().label("count")
            )
            .where(and_(*filters_granted))
            .group_by(func.date(DpdpConsent.granted_at))
        )

        withdrawn_stmt = (
            select(
                func.date(DpdpConsent.withdrawn_at).label("date"),
                func.count().label("count")
            )
            .where(and_(*filters_withdrawn))
            .group_by(func.date(DpdpConsent.withdrawn_at))
        )

        granted_result = await self.session.execute(granted_stmt)
        withdrawn_result = await self.session.execute(withdrawn_stmt)

        granted_data = {str(row[0]): row[1] for row in granted_result}
        withdrawn_data = {str(row[0]): row[1] for row in withdrawn_result}

        all_dates = sorted(set(granted_data.keys()) | set(withdrawn_data.keys()))

        items = [
            {
                "date": date_str,
                "granted": granted_data.get(date_str, 0),
                "withdrawn": withdrawn_data.get(date_str, 0),
            }
            for date_str in all_dates
        ]

        return StandardResponse.success(
            data={"items": items, "days": days},
            message="Consent trend retrieved successfully",
        ).make

    async def get_summary(
        self,
        org_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get consent summary statistics.

        Args:
            org_id: Optional organization ID filter
            from_date: ISO datetime string for filter start
            to_date: ISO datetime string for filter end

        Returns:
            Standard response with summary statistics
        """
        from_dt = None
        to_dt = None

        try:
            if from_date:
                from_dt = datetime.fromisoformat(from_date)
            if to_date:
                to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            return StandardResponse.bad_request(
                message="Invalid date format. Use ISO datetime.",
                data={"error": "INVALID_DATE_FORMAT"},
            ).make

        filters = []
        if org_id:
            filters.append(ConsentForm.org_id == org_id)
            filters_consent = [
                DpdpConsent.form_id.in_(
                    select(ConsentForm.id).where(ConsentForm.org_id == org_id)
                )
            ]
        else:
            filters_consent = []

        if from_dt:
            filters_consent.append(DpdpConsent.created_at >= from_dt)
        if to_dt:
            filters_consent.append(DpdpConsent.created_at <= to_dt)

        granted_stmt = (
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                and_(
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                    *filters_consent
                )
            )
        )

        withdrawn_stmt = (
            select(func.count())
            .select_from(DpdpConsent)
            .where(
                and_(
                    DpdpConsent.status == ConsentStatus.WITHDRAWN.value,
                    *filters_consent
                )
            )
        )

        total_granted = await self.session.scalar(granted_stmt) or 0
        total_withdrawn = await self.session.scalar(withdrawn_stmt) or 0

        total = total_granted + total_withdrawn
        withdrawal_rate = (
            total_withdrawn / total if total > 0 else 0.0
        )
        acceptance_rate = (
            total_granted / total if total > 0 else 0.0
        )

        reconsent_stmt = (
            select(func.count(func.distinct(DpdpConsent.user_id)))
            .select_from(DpdpConsent)
            .join(ConsentForm, DpdpConsent.form_id == ConsentForm.id)
            .where(
                and_(
                    DpdpConsent.version != ConsentForm.active_version,
                    DpdpConsent.status == ConsentStatus.GRANTED.value,
                    *filters_consent
                )
            )
        )

        pending_re_consent = await self.session.scalar(reconsent_stmt) or 0

        return StandardResponse.success(
            data={
                "total_granted": total_granted,
                "total_withdrawn": total_withdrawn,
                "withdrawal_rate": round(withdrawal_rate, 4),
                "acceptance_rate": round(acceptance_rate, 4),
                "pending_re_consent": pending_re_consent,
            },
            message="Consent summary retrieved successfully",
        ).make

    async def get_forms_by_status(
        self, org_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get count of forms by status.

        Args:
            org_id: Optional organization ID filter

        Returns:
            Standard response with form status counts
        """
        filters = []
        if org_id:
            filters.append(ConsentForm.org_id == org_id)

        statuses = ["active", "draft", "in_review", "archived", "deactivated"]
        counts = {}

        for status in statuses:
            stmt = (
                select(func.count())
                .select_from(ConsentForm)
                .where(
                    and_(
                        ConsentForm.status == status,
                        *filters
                    )
                )
            )
            count = await self.session.scalar(stmt) or 0
            counts[status] = count

        return StandardResponse.success(
            data=counts,
            message="Forms by status retrieved successfully",
        ).make

    async def get_top_forms(
        self,
        limit: int = 5,
        org_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get top forms by consent grants.

        Args:
            limit: Number of top forms to return
            org_id: Optional organization ID filter

        Returns:
            Standard response with top forms
        """
        filters = []
        if org_id:
            filters.append(ConsentForm.org_id == org_id)

        stmt = (
            select(
                ConsentForm.id,
                ConsentForm.name,
                func.count(
                    func.case(
                        (DpdpConsent.status == ConsentStatus.GRANTED.value, 1),
                        else_=None
                    )
                ).label("granted"),
                func.count(
                    func.case(
                        (DpdpConsent.status == ConsentStatus.WITHDRAWN.value, 1),
                        else_=None
                    )
                ).label("withdrawn"),
            )
            .select_from(ConsentForm)
            .outerjoin(DpdpConsent, ConsentForm.id == DpdpConsent.form_id)
        )

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = (
            stmt
            .group_by(ConsentForm.id, ConsentForm.name)
            .order_by(func.count(
                func.case(
                    (DpdpConsent.status == ConsentStatus.GRANTED.value, 1),
                    else_=None
                )
            ).desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = []
        for row in rows:
            form_id, name, granted, withdrawn = row
            total = granted + withdrawn
            acceptance_rate = granted / total if total > 0 else 0.0

            items.append({
                "form_id": form_id,
                "name": name,
                "granted": granted or 0,
                "withdrawn": withdrawn or 0,
                "acceptance_rate": round(acceptance_rate, 4),
            })

        return StandardResponse.success(
            data={"items": items, "limit": limit},
            message="Top forms retrieved successfully",
        ).make
