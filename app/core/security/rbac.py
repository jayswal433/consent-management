from __future__ import annotations

import os
from enum import Enum
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User role enumeration for DPDP system."""

    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    FORM_EDITOR = "form_editor"
    DPO_REVIEWER = "dpo_reviewer"
    READ_ONLY_ANALYST = "read_only_analyst"
    CITIZEN = "citizen"
    SYSTEM_SERVICE = "system_service"


class Permission(str, Enum):
    """Permission enumeration for DPDP system."""

    CREATE_DELETE_ORG = "create_delete_org"
    VIEW_ORG_PROFILE = "view_org_profile"
    UPDATE_ORG_SETTINGS = "update_org_settings"
    MANAGE_TEAM_MEMBERS = "manage_team_members"

    CREATE_CONSENT_FORM = "create_consent_form"
    EDIT_FORM_DRAFT = "edit_form_draft"
    SUBMIT_FOR_REVIEW = "submit_for_review"
    APPROVE_PUBLISH_VERSION = "approve_publish_version"
    ROLLBACK_VERSION = "rollback_version"
    ACTIVATE_DEACTIVATE_FORM = "activate_deactivate_form"
    VIEW_FORM_DETAILS = "view_form_details"

    GRANT_CONSENT = "grant_consent"
    WITHDRAW_CONSENT = "withdraw_consent"
    VIEW_OWN_CONSENTS = "view_own_consents"
    DOWNLOAD_CONSENT_RECEIPT = "download_consent_receipt"
    VIEW_ALL_CONSENTS = "view_all_consents"
    CHECK_CONSENT_SERVICE = "check_consent_service"
    BULK_REVOKE = "bulk_revoke"

    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"

    TRIGGER_NOTIFICATIONS = "trigger_notifications"

    VIEW_ANALYTICS = "view_analytics"

    EXPORT_USER_DATA = "export_user_data"
    REGISTER_NOMINEE = "register_nominee"
    ERASURE_REQUEST = "erasure_request"

    ISSUE_JWT = "issue_jwt"
    REVOKE_TOKEN = "revoke_token"
    INTROSPECT_TOKEN = "introspect_token"
    MANAGE_RBAC_ROLES = "manage_rbac_roles"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.SUPER_ADMIN: {
        Permission.CREATE_DELETE_ORG,
        Permission.VIEW_ORG_PROFILE,
        Permission.UPDATE_ORG_SETTINGS,
        Permission.MANAGE_TEAM_MEMBERS,
        Permission.CREATE_CONSENT_FORM,
        Permission.EDIT_FORM_DRAFT,
        Permission.SUBMIT_FOR_REVIEW,
        Permission.APPROVE_PUBLISH_VERSION,
        Permission.ROLLBACK_VERSION,
        Permission.ACTIVATE_DEACTIVATE_FORM,
        Permission.VIEW_FORM_DETAILS,
        Permission.DOWNLOAD_CONSENT_RECEIPT,
        Permission.VIEW_ALL_CONSENTS,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT_LOG,
        Permission.TRIGGER_NOTIFICATIONS,
        Permission.VIEW_ANALYTICS,
        Permission.ISSUE_JWT,
        Permission.REVOKE_TOKEN,
        Permission.MANAGE_RBAC_ROLES,
    },
    UserRole.ORG_ADMIN: {
        Permission.VIEW_ORG_PROFILE,
        Permission.UPDATE_ORG_SETTINGS,
        Permission.MANAGE_TEAM_MEMBERS,
        Permission.CREATE_CONSENT_FORM,
        Permission.EDIT_FORM_DRAFT,
        Permission.SUBMIT_FOR_REVIEW,
        Permission.APPROVE_PUBLISH_VERSION,
        Permission.ROLLBACK_VERSION,
        Permission.ACTIVATE_DEACTIVATE_FORM,
        Permission.VIEW_FORM_DETAILS,
        Permission.DOWNLOAD_CONSENT_RECEIPT,
        Permission.VIEW_ALL_CONSENTS,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT_LOG,
        Permission.TRIGGER_NOTIFICATIONS,
        Permission.VIEW_ANALYTICS,
        Permission.REVOKE_TOKEN,
    },
    UserRole.FORM_EDITOR: {
        Permission.VIEW_ORG_PROFILE,
        Permission.CREATE_CONSENT_FORM,
        Permission.EDIT_FORM_DRAFT,
        Permission.SUBMIT_FOR_REVIEW,
        Permission.VIEW_FORM_DETAILS,
    },
    UserRole.DPO_REVIEWER: {
        Permission.VIEW_ORG_PROFILE,
        Permission.APPROVE_PUBLISH_VERSION,
        Permission.VIEW_FORM_DETAILS,
        Permission.VIEW_ALL_CONSENTS,
        Permission.VIEW_AUDIT_LOG,
        Permission.EXPORT_AUDIT_LOG,
        Permission.VIEW_ANALYTICS,
    },
    UserRole.READ_ONLY_ANALYST: {
        Permission.VIEW_ORG_PROFILE,
        Permission.VIEW_FORM_DETAILS,
        Permission.VIEW_ALL_CONSENTS,
        Permission.VIEW_AUDIT_LOG,
        Permission.VIEW_ANALYTICS,
    },
    UserRole.CITIZEN: {
        Permission.GRANT_CONSENT,
        Permission.WITHDRAW_CONSENT,
        Permission.VIEW_OWN_CONSENTS,
        Permission.DOWNLOAD_CONSENT_RECEIPT,
        Permission.ISSUE_JWT,
        Permission.REVOKE_TOKEN,
        Permission.EXPORT_USER_DATA,
        Permission.REGISTER_NOMINEE,
        Permission.ERASURE_REQUEST,
    },
    UserRole.SYSTEM_SERVICE: {
        Permission.VIEW_ORG_PROFILE,
        Permission.GRANT_CONSENT,
        Permission.VIEW_FORM_DETAILS,
        Permission.VIEW_ALL_CONSENTS,
        Permission.CHECK_CONSENT_SERVICE,
        Permission.BULK_REVOKE,
        Permission.TRIGGER_NOTIFICATIONS,
        Permission.ISSUE_JWT,
        Permission.INTROSPECT_TOKEN,
    },
}


async def get_jwt_claims(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    """
    Extract and validate JWT token, returning claims dictionary.

    Reads the JWT_SECRET_KEY and JWT_ALGORITHM from environment and decodes
    the Bearer token. Returns the decoded claims dictionary including sub,
    role, and org_id fields.

    Args:
        credentials: HTTP Authorization credentials from Bearer token.

    Returns:
        Decoded JWT claims dictionary.

    Raises:
        HTTPException: If credentials are missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "MISSING_CREDENTIALS", "message": "No bearer token provided"},
        )

    jwt_secret = os.getenv("JWT_SECRET_KEY", "consent-management-secret-change-me")
    jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    try:
        payload = jwt.decode(
            credentials.credentials, jwt_secret, algorithms=[jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "TOKEN_EXPIRED", "message": "Token has expired"},
        ) from e
    except jwt.InvalidSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_SIGNATURE", "message": "Invalid token signature"},
        ) from e
    except jwt.DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "DECODE_ERROR", "message": "Failed to decode token"},
        ) from e


def require_permission(permission: Permission) -> callable:
    """
    Create a FastAPI dependency that checks for a specific permission.

    Extracts the role from JWT claims and verifies it has the required
    permission according to ROLE_PERMISSIONS matrix. Super admins bypass
    all permission checks.

    Args:
        permission: The permission to check.

    Returns:
        Async dependency function that validates permission.

    Raises:
        HTTPException: If permission is not granted.
    """

    async def _check_permission(
        token_data: dict[str, Any] = Depends(get_jwt_claims),
    ) -> dict[str, Any]:
        """
        Check if token_data has the required permission.

        Args:
            token_data: Decoded JWT claims from get_jwt_claims dependency.

        Returns:
            The token_data dict if permission is granted.

        Raises:
            HTTPException: If permission is insufficient.
        """
        role_str = token_data.get("role")

        if not role_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "NO_ROLE",
                    "message": "No role found in token",
                },
            )

        try:
            role = UserRole(role_str)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INVALID_ROLE",
                    "message": f"Unknown role: {role_str}",
                },
            ) from e

        allowed_permissions = ROLE_PERMISSIONS.get(role, set())

        if permission not in allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "INSUFFICIENT_SCOPE",
                    "message": f"Permission '{permission.value}' required",
                },
            )

        return token_data

    return _check_permission
