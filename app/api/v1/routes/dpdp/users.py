from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.schemas.dpdp.user import (
    DpdpUserCreateRequest,
    ErasureRequest,
    NomineeCreateRequest,
    PortabilityRequest,
)
from app.services.dpdp.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"], include_in_schema=False)


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    token_data: Annotated[dict, Depends(get_jwt_claims)],
    session: AsyncSession = Depends(get_db_session),
):
    requester_id = token_data.get("sub")
    requester_role = token_data.get("role")

    is_self = requester_id == user_id
    is_admin = requester_role in ["super_admin", "org_admin"]

    if not (is_self or is_admin):
        from app.core.responses import StandardResponse
        return StandardResponse.forbidden(
            message="Access denied",
            data={"error": "ACCESS_DENIED"},
        ).make

    service = UserService(session)
    return await service.get_user(user_id, requester_id, requester_role)


@router.get("")
async def list_users(
    token_data: Annotated[dict, Depends(require_permission(Permission.VIEW_ORG_PROFILE))],
    session: AsyncSession = Depends(get_db_session),
    org_id: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    service = UserService(session)
    return await service.list_users(org_id, page, limit)


@router.get("/{user_id}/consents")
async def get_user_consents(
    user_id: str,
    token_data: Annotated[dict, Depends(get_jwt_claims)],
    session: AsyncSession = Depends(get_db_session),
    status: str | None = None,
):
    requester_id = token_data.get("sub")
    requester_role = token_data.get("role")

    is_self = requester_id == user_id
    has_view_all = requester_role in ["super_admin", "org_admin", "dpo_reviewer"]

    if not (is_self or has_view_all):
        from app.core.responses import StandardResponse
        return StandardResponse.forbidden(
            message="Access denied",
            data={"error": "ACCESS_DENIED"},
        ).make

    service = UserService(session)
    return await service.get_user_consents(user_id, status)


@router.get("/{user_id}/rights")
async def get_user_rights(
    user_id: str,
    token_data: Annotated[dict, Depends(get_jwt_claims)],
    session: AsyncSession = Depends(get_db_session),
):
    requester_id = token_data.get("sub")
    requester_role = token_data.get("role")

    is_self = requester_id == user_id
    is_admin = requester_role in ["super_admin", "org_admin"]

    if not (is_self or is_admin):
        from app.core.responses import StandardResponse
        return StandardResponse.forbidden(
            message="Access denied",
            data={"error": "ACCESS_DENIED"},
        ).make

    service = UserService(session)
    return await service.get_user_rights(user_id)


@router.post("/{user_id}/rights/erasure")
async def request_erasure(
    user_id: str,
    data: ErasureRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.ERASURE_REQUEST))],
    session: AsyncSession = Depends(get_db_session),
):
    actor_id = token_data.get("sub")
    service = UserService(session)
    return await service.erasure(user_id, data, actor_id)


@router.post("/{user_id}/rights/portability")
async def request_portability(
    user_id: str,
    data: PortabilityRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.EXPORT_USER_DATA))],
    session: AsyncSession = Depends(get_db_session),
):
    actor_id = token_data.get("sub")
    service = UserService(session)
    return await service.portability(user_id, data, actor_id)


@router.post("/{user_id}/nominee")
async def register_nominee(
    user_id: str,
    data: NomineeCreateRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.REGISTER_NOMINEE))],
    session: AsyncSession = Depends(get_db_session),
):
    actor_id = token_data.get("sub")
    service = UserService(session)
    return await service.register_nominee(user_id, data, actor_id)


@router.post("")
async def create_user(
    data: DpdpUserCreateRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.MANAGE_TEAM_MEMBERS))],
    session: AsyncSession = Depends(get_db_session),
):
    service = UserService(session)
    return await service.create_user(data)
