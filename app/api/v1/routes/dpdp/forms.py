from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.database import get_db_session
from app.core.responses import StandardResponse
from app.core.security.rbac import Permission, get_jwt_claims, require_permission
from app.schemas.dpdp.form import (
    CreateFormRequest,
    DeactivateFormRequest,
    FormCreateResponse,
    FormDetailResponse,
    FormListItem,
    LatestPublishedFormResponse,
    PublishedFormItem,
    UpdateFormRequest,
)
from app.services.dpdp.form_service import FormService

router = APIRouter(prefix="/forms", tags=["Forms"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def list_forms(
    status_filter: str | None = Query(None, alias="status"),
    owner: str | None = Query(None),
    q: str | None = Query(None),
    sort_by: str = Query("created_at"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.VIEW_FORM_DETAILS)),
):
    service = FormService(session)
    result = await service.list_forms(
        status=status_filter,
        owner=owner,
        q=q,
        sort_by=sort_by,
        page=page,
        limit=limit,
    )

    return StandardResponse.success(
        data=result,
        message="Forms retrieved successfully",
    ).make


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_form(
    request: CreateFormRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.CREATE_CONSENT_FORM)),
):
    service = FormService(session)
    result = await service.create_form(request, actor_id=claims.get("sub"))

    if isinstance(result, dict) and "error" in result:
        status_code = result.get("status_code", 400)
        if status_code == 409:
            return StandardResponse.conflict(
                message=result["message"],
            ).make
        return StandardResponse.bad_request(
            message=result["message"],
        ).make

    return StandardResponse.created(
        data=result,
        message="Form created successfully",
    ).make


@router.get(
    "/org/{org_id}/published",
    status_code=status.HTTP_200_OK,
)
async def get_published_forms_by_org(
    org_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.VIEW_FORM_DETAILS)),
):
    service = FormService(session)
    items = await service.get_published_forms_by_org(org_id)

    return StandardResponse.success(
        data={"items": items, "total": len(items)},
        message="Published forms retrieved successfully",
    ).make


@router.get(
    "/org/{org_id}/latest-published",
    status_code=status.HTTP_200_OK,
)
async def get_latest_published_form_by_org(
    org_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    service = FormService(session)
    result = await service.get_latest_published_form_by_org(org_id)

    if not result:
        return StandardResponse.not_found(
            message=f"No published form found for organization {org_id}",
        ).make

    return StandardResponse.success(
        data=result,
        message="Latest published form retrieved successfully",
    ).make


@router.get(
    "/{form_id}",
    status_code=status.HTTP_200_OK,
)
async def get_form(
    form_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.VIEW_FORM_DETAILS)),
):
    service = FormService(session)
    result = await service.get_form(form_id)

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    return StandardResponse.success(
        data=result,
        message="Form retrieved successfully",
    ).make


@router.patch(
    "/{form_id}",
    status_code=status.HTTP_200_OK,
)
async def update_form(
    form_id: str,
    request: UpdateFormRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.EDIT_FORM_DRAFT)),
):
    service = FormService(session)
    result = await service.update_form(
        form_id, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    if isinstance(result, dict) and "error" in result:
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Form updated successfully",
    ).make


@router.delete(
    "/{form_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_form(
    form_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.ACTIVATE_DEACTIVATE_FORM)),
):
    service = FormService(session)
    result = await service.delete_form(form_id, actor_id=claims.get("sub"))

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    if isinstance(result, dict) and "error" in result:
        status_code = result.get("status_code", 400)
        if status_code == 403:
            return StandardResponse.forbidden(
                message=result["message"],
            ).make
        return StandardResponse.bad_request(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Form deleted successfully",
    ).make


@router.post(
    "/{form_id}/activate",
    status_code=status.HTTP_200_OK,
)
async def activate_form(
    form_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.ACTIVATE_DEACTIVATE_FORM)),
):
    service = FormService(session)
    result = await service.activate_form(form_id, actor_id=claims.get("sub"))

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    if isinstance(result, dict) and "error" in result:
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Form activated successfully",
    ).make


@router.post(
    "/{form_id}/deactivate",
    status_code=status.HTTP_200_OK,
)
async def deactivate_form(
    form_id: str,
    request: DeactivateFormRequest,
    session: AsyncSession = Depends(get_db_session),
    claims: dict = Depends(get_jwt_claims),
    _: Any = Depends(require_permission(Permission.ACTIVATE_DEACTIVATE_FORM)),
):
    service = FormService(session)
    result = await service.deactivate_form(
        form_id, request, actor_id=claims.get("sub")
    )

    if not result:
        return StandardResponse.not_found(
            message=f"Form {form_id} not found",
        ).make

    if isinstance(result, dict) and "error" in result:
        return StandardResponse.forbidden(
            message=result["message"],
        ).make

    return StandardResponse.success(
        data=result,
        message="Form deactivated successfully",
    ).make
