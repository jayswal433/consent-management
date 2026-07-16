from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.responses import StandardResponse
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.schemas.dpdp.version import (
    CreateVersionRequest,
    PublishVersionRequest,
    RollbackVersionRequest,
    SubmitVersionRequest,
    UpdateVersionRequest,
    VersionDiffResponse,
)
from app.services.dpdp.version_service import VersionService

router = APIRouter(prefix="/forms", tags=["Form Versions"])


@router.get(
    "/{form_id}/versions",
    status_code=status.HTTP_200_OK,
)
async def list_versions(
    form_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.VIEW_FORM_DETAILS)),
):
    service = VersionService(session)
    result = await service.list_versions(form_id)

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    return StandardResponse.success(
        data=result,
        message="Versions retrieved successfully",
    ).make


@router.post(
    "/{form_id}/versions",
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    form_id: str,
    request: CreateVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.CREATE_CONSENT_FORM)),
):
    service = VersionService(session)
    result = await service.create_version(
        form_id, request, actor_id=claims.get("sub")
    )

    if isinstance(result, dict) and "error" in result:
        status_code = result.get("status_code", 400)
        if status_code == 404:
            return StandardResponse.not_found(
                message=result["message"],
            ).make
        if status_code == 409:
            return StandardResponse.conflict(
                message=result["message"],
            ).make
        return StandardResponse.bad_request(
            message=result["message"],
        ).make

    return StandardResponse.created(
        data=result,
        message="Version created successfully",
    ).make


@router.patch(
    "/{form_id}/versions/{version}",
    status_code=status.HTTP_200_OK,
)
async def update_version(
    form_id: str,
    version: str,
    request: UpdateVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.EDIT_FORM_DRAFT)),
):
    service = VersionService(session)
    result = await service.update_version(
        form_id, version, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Version {version} not found in form {form_id}",
        ).make

    if isinstance(result, dict) and "error" in result:
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Version updated successfully",
    ).make


@router.post(
    "/{form_id}/versions/{version}/submit",
    status_code=status.HTTP_200_OK,
)
async def submit_version(
    form_id: str,
    version: str,
    request: SubmitVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.SUBMIT_FOR_REVIEW)),
):
    service = VersionService(session)
    result = await service.submit_version(
        form_id, version, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Version {version} not found in form {form_id}",
        ).make

    if isinstance(result, dict) and "error" in result:
        status_code = result.get("status_code", 400)
        if status_code == 409:
            return StandardResponse.conflict(
                message=result["message"],
            ).make
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Version submitted for review successfully",
    ).make


@router.post(
    "/{form_id}/versions/{version}/publish",
    status_code=status.HTTP_200_OK,
)
async def publish_version(
    form_id: str,
    version: str,
    request: PublishVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.APPROVE_PUBLISH_VERSION)),
):
    service = VersionService(session)
    result = await service.publish_version(
        form_id, version, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Version {version} not found in form {form_id}",
        ).make

    if isinstance(result, dict) and "error" in result:
        status_code = result.get("status_code", 400)
        if status_code == 422:
            return StandardResponse.validation_error(
                message=result["message"],
            ).make
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Version published successfully",
    ).make


@router.post(
    "/{form_id}/versions/{version}/rollback",
    status_code=status.HTTP_200_OK,
)
async def rollback_version(
    form_id: str,
    version: str,
    request: RollbackVersionRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.ROLLBACK_VERSION)),
):
    service = VersionService(session)
    result = await service.rollback_version(
        form_id, version, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Version {version} not found in form {form_id}",
        ).make

    if isinstance(result, dict) and "error" in result:
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Version rolled back successfully",
    ).make


@router.get(
    "/{form_id}/versions/diff",
    status_code=status.HTTP_200_OK,
)
async def get_version_diff(
    form_id: str,
    from_version: str = Query(...),
    to_version: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.VIEW_FORM_DETAILS)),
):
    service = VersionService(session)
    result = await service.get_version_diff(form_id, from_version, to_version)

    if not result:
        return StandardResponse.not_found(
            message=(
                f"Form {form_id} or one of the versions "
                f"({from_version}, {to_version}) not found"
            ),
        ).make

    return StandardResponse.success(
        data=result,
        message="Version diff retrieved successfully",
    ).make
