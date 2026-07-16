from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.responses import StandardResponse
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.schemas.dpdp.auth_dpdp import (
    BootstrapRequest,
    IntrospectRequest,
    RefreshRequest,
    RegisterRequest,
    RevokeRequest,
    TokenRequest,
)
from app.services.dpdp.auth_dpdp_service import AuthDpdpService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/bootstrap")
async def bootstrap_system(
    data: BootstrapRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """One-time endpoint: creates the first super_admin. Disabled once any super_admin exists."""
    service = AuthDpdpService(session)
    return await service.bootstrap(data)


@router.post("/register")
async def register_user(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Public self-registration. Always creates a citizen-role user."""
    service = AuthDpdpService(session)
    return await service.register(data)


@router.post("/token")
async def issue_token(
    data: TokenRequest,
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthDpdpService(session)
    result = await service.issue_token(data)
    return result


@router.post("/refresh")
async def refresh_token(
    data: RefreshRequest,
    token_data: Annotated[dict, Depends(get_jwt_claims)],
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthDpdpService(session)
    result = await service.refresh_token(data)
    return result


@router.post("/revoke")
async def revoke_token(
    data: RevokeRequest,
    token_data: Annotated[dict, Depends(get_jwt_claims)],
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthDpdpService(session)
    result = await service.revoke_token(data)
    return result


@router.post("/introspect")
async def introspect_token(
    data: IntrospectRequest,
    token_data: Annotated[dict, Depends(require_permission(Permission.INTROSPECT_TOKEN))],
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthDpdpService(session)
    result = await service.introspect_token(data)
    return result


@router.get("/roles")
async def list_roles(
    token_data: Annotated[dict, Depends(require_permission(Permission.MANAGE_RBAC_ROLES))],
    session: AsyncSession = Depends(get_db_session),
):
    service = AuthDpdpService(session)
    result = service.list_roles()
    return result
