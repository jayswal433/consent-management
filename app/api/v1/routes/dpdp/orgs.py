from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, require_permission
from app.schemas.dpdp.org import OrgCreateRequest, OrgUpdateRequest
from app.services.dpdp.org_service import OrgService

router = APIRouter(prefix="/orgs", tags=["Orgs"])


@router.get("/{org_id}")
async def get_org(
    org_id: str,
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ORG_PROFILE))],
    session: AsyncSession = Depends(get_db_session),
):
    service = OrgService(session)
    return await service.get_org(org_id)


@router.get("")
async def list_orgs(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    token_data: Annotated[dict, Depends(require_permission(Permission.CREATE_DELETE_ORG))] = None,
    session: AsyncSession = Depends(get_db_session),
):
    service = OrgService(session)
    return await service.list_orgs(page, limit)


@router.post("")
async def create_org(
    data: OrgCreateRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.CREATE_DELETE_ORG))],
    session: AsyncSession = Depends(get_db_session),
):
    actor_id = token_data.get("sub")
    service = OrgService(session)
    return await service.create_org(data, actor_id)


@router.patch("/{org_id}")
async def update_org(
    org_id: str,
    data: OrgUpdateRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.UPDATE_ORG_SETTINGS))],
    session: AsyncSession = Depends(get_db_session),
):
    actor_id = token_data.get("sub")
    service = OrgService(session)
    return await service.update_org(org_id, data, actor_id)
