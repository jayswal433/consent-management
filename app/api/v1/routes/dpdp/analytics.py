from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, require_permission
from app.services.dpdp.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/consent-trend")
async def get_consent_trend(
    days: Annotated[int, Query(ge=1)] = 30,
    form_id: Annotated[str | None, Query()] = None,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ANALYTICS))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get consent trend data for the last N days."""
    service = AnalyticsService(session)
    return await service.get_consent_trend(days=days, form_id=form_id)


@router.get("/summary")
async def get_summary(
    org_id: Annotated[str | None, Query()] = None,
    from_date: Annotated[str | None, Query()] = None,
    to_date: Annotated[str | None, Query()] = None,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ANALYTICS))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get consent summary statistics."""
    service = AnalyticsService(session)
    return await service.get_summary(
        org_id=org_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/forms-by-status")
async def get_forms_by_status(
    org_id: Annotated[str | None, Query()] = None,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ANALYTICS))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get form count breakdown by status."""
    service = AnalyticsService(session)
    return await service.get_forms_by_status(org_id=org_id)


@router.get("/top-forms")
async def get_top_forms(
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
    org_id: Annotated[str | None, Query()] = None,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ANALYTICS))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Get top forms by consent grants."""
    service = AnalyticsService(session)
    return await service.get_top_forms(limit=limit, org_id=org_id)
