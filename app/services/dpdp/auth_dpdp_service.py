from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.core.responses import StandardResponse
from app.core.security.crypto import encrypt_field, get_dek, sha256_hash
from app.core.security.rbac import ROLE_PERMISSIONS, UserRole
from app.models.orm.dpdp_user import DpdpUser
from app.repositories.dpdp_user_repository import DpdpUserRepository
from app.schemas.dpdp.auth_dpdp import (
    BootstrapRequest,
    IntrospectRequest,
    RefreshRequest,
    RegisterRequest,
    RevokeRequest,
    TokenRequest,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ACCESS_TOKEN_TTL = 900
REFRESH_TOKEN_TTL = 604800
_token_blacklist = set()


class AuthDpdpService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DpdpUserRepository(session)
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "consent-management-secret-change-me")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    async def issue_token(self, data: TokenRequest) -> dict[str, Any]:
        if data.grant_type == "password":
            return await self._issue_token_password(data)
        elif data.grant_type == "client_credentials":
            return await self._issue_token_client_credentials(data)
        else:
            return StandardResponse.bad_request(
                message="Unsupported grant type",
                data={"error": "UNSUPPORTED_GRANT_TYPE"},
            ).make

    async def _issue_token_password(self, data: TokenRequest) -> dict[str, Any]:
        if not data.username or not data.password:
            return StandardResponse.bad_request(
                message="Username and password required",
                data={"error": "MISSING_CREDENTIALS"},
            ).make

        from app.core.security.crypto import sha256_hash

        email_hash = sha256_hash(data.username.lower())
        user = await self.repo.get_by_email_hash(email_hash)

        if not user:
            return StandardResponse.unauthorized(
                message="Invalid credentials",
                data={"error": "INVALID_CREDENTIALS"},
            ).make

        if not pwd_context.verify(data.password, user.password_hash):
            return StandardResponse.unauthorized(
                message="Invalid credentials",
                data={"error": "INVALID_CREDENTIALS"},
            ).make

        if user.is_active != "1":
            return StandardResponse.forbidden(
                message="User account is inactive",
                data={"error": "USER_INACTIVE"},
            ).make

        now = int(time.time())
        access_token_payload = {
            "sub": user.id,
            "role": user.role,
            "org_id": user.org_id,
            "type": "access",
            "exp": now + ACCESS_TOKEN_TTL,
            "iat": now,
        }

        refresh_token_jti = str(uuid.uuid4())
        refresh_token_payload = {
            "sub": user.id,
            "type": "refresh",
            "jti": refresh_token_jti,
            "exp": now + REFRESH_TOKEN_TTL,
            "iat": now,
        }

        try:
            access_token = jwt.encode(
                access_token_payload, self.jwt_secret, algorithm=self.jwt_algorithm
            )
            refresh_token = jwt.encode(
                refresh_token_payload, self.jwt_secret, algorithm=self.jwt_algorithm
            )
        except Exception as e:
            return StandardResponse.internal_error(
                message="Token generation failed",
                data={"error": "TOKEN_GENERATION_FAILED"},
            ).make

        permissions = ROLE_PERMISSIONS.get(UserRole(user.role), set())
        scope = " ".join([p.value for p in permissions])

        return StandardResponse.success(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": ACCESS_TOKEN_TTL,
                "scope": scope,
                "token_type": "Bearer",
            },
            message="Token issued successfully",
        ).make

    async def _issue_token_client_credentials(self, data: TokenRequest) -> dict[str, Any]:
        if not data.client_id or not data.client_secret:
            return StandardResponse.bad_request(
                message="Client ID and secret required",
                data={"error": "MISSING_CLIENT_CREDENTIALS"},
            ).make

        if data.client_id != os.getenv("DPDP_CLIENT_ID", "dpdp-system"):
            return StandardResponse.unauthorized(
                message="Invalid client credentials",
                data={"error": "INVALID_CLIENT"},
            ).make

        if data.client_secret != os.getenv("DPDP_CLIENT_SECRET", "dpdp-secret"):
            return StandardResponse.unauthorized(
                message="Invalid client credentials",
                data={"error": "INVALID_CLIENT"},
            ).make

        now = int(time.time())
        access_token_payload = {
            "sub": "system-service",
            "role": UserRole.SYSTEM_SERVICE.value,
            "org_id": None,
            "type": "access",
            "exp": now + ACCESS_TOKEN_TTL,
            "iat": now,
        }

        try:
            access_token = jwt.encode(
                access_token_payload, self.jwt_secret, algorithm=self.jwt_algorithm
            )
        except Exception:
            return StandardResponse.internal_error(
                message="Token generation failed",
                data={"error": "TOKEN_GENERATION_FAILED"},
            ).make

        permissions = ROLE_PERMISSIONS.get(UserRole.SYSTEM_SERVICE, set())
        scope = " ".join([p.value for p in permissions])

        return StandardResponse.success(
            data={
                "access_token": access_token,
                "refresh_token": "",
                "expires_in": ACCESS_TOKEN_TTL,
                "scope": scope,
                "token_type": "Bearer",
            },
            message="Token issued successfully",
        ).make

    async def refresh_token(self, data: RefreshRequest) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                data.refresh_token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            return StandardResponse.unauthorized(
                message="Refresh token has expired",
                data={"error": "TOKEN_EXPIRED"},
            ).make
        except jwt.InvalidSignatureError:
            return StandardResponse.unauthorized(
                message="Invalid refresh token signature",
                data={"error": "INVALID_SIGNATURE"},
            ).make
        except jwt.DecodeError:
            return StandardResponse.unauthorized(
                message="Failed to decode refresh token",
                data={"error": "DECODE_ERROR"},
            ).make

        if payload.get("type") != "refresh":
            return StandardResponse.bad_request(
                message="Token is not a refresh token",
                data={"error": "INVALID_TOKEN_TYPE"},
            ).make

        jti = payload.get("jti")
        if jti in _token_blacklist:
            return StandardResponse.unauthorized(
                message="Refresh token has been revoked",
                data={"error": "TOKEN_REVOKED"},
            ).make

        user_id = payload.get("sub")
        user = await self.repo.get_by_id(user_id)

        if not user:
            return StandardResponse.unauthorized(
                message="User not found",
                data={"error": "USER_NOT_FOUND"},
            ).make

        if user.is_active != "1":
            return StandardResponse.forbidden(
                message="User account is inactive",
                data={"error": "USER_INACTIVE"},
            ).make

        now = int(time.time())
        new_access_token_payload = {
            "sub": user_id,
            "role": user.role,
            "org_id": user.org_id,
            "type": "access",
            "exp": now + ACCESS_TOKEN_TTL,
            "iat": now,
        }

        try:
            new_access_token = jwt.encode(
                new_access_token_payload,
                self.jwt_secret,
                algorithm=self.jwt_algorithm,
            )
        except Exception:
            return StandardResponse.internal_error(
                message="Token generation failed",
                data={"error": "TOKEN_GENERATION_FAILED"},
            ).make

        permissions = ROLE_PERMISSIONS.get(UserRole(user.role), set())
        scope = " ".join([p.value for p in permissions])

        return StandardResponse.success(
            data={
                "access_token": new_access_token,
                "refresh_token": data.refresh_token,
                "expires_in": ACCESS_TOKEN_TTL,
                "scope": scope,
                "token_type": "Bearer",
            },
            message="Token refreshed successfully",
        ).make

    async def revoke_token(self, data: RevokeRequest) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                data.token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            return StandardResponse.success(
                message="Token already expired"
            ).make
        except jwt.InvalidSignatureError:
            return StandardResponse.unauthorized(
                message="Invalid token signature",
                data={"error": "INVALID_SIGNATURE"},
            ).make
        except jwt.DecodeError:
            return StandardResponse.unauthorized(
                message="Failed to decode token",
                data={"error": "DECODE_ERROR"},
            ).make

        token_type = payload.get("type")
        jti = payload.get("jti")

        if token_type == "refresh" and jti:
            _token_blacklist.add(jti)

        return StandardResponse.success(message="Token revoked successfully").make

    async def introspect_token(self, data: IntrospectRequest) -> dict[str, Any]:
        try:
            payload = jwt.decode(
                data.token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
        except jwt.ExpiredSignatureError:
            return StandardResponse.success(
                data={
                    "active": False,
                    "scope": None,
                    "sub": None,
                    "exp": None,
                }
            ).make
        except (jwt.InvalidSignatureError, jwt.DecodeError):
            return StandardResponse.success(
                data={
                    "active": False,
                    "scope": None,
                    "sub": None,
                    "exp": None,
                }
            ).make

        user_id = payload.get("sub")
        role = payload.get("role")
        exp = payload.get("exp")

        permissions = ROLE_PERMISSIONS.get(UserRole(role), set())
        scope = " ".join([p.value for p in permissions])

        return StandardResponse.success(
            data={
                "active": True,
                "scope": scope,
                "sub": user_id,
                "exp": exp,
            }
        ).make

    async def register(self, data: RegisterRequest) -> dict[str, Any]:
        email_hash = sha256_hash(data.email.lower())
        existing = await self.repo.get_by_email_hash(email_hash)
        if existing:
            return StandardResponse.conflict(
                message="Email already registered",
                data={"error": "DUPLICATE_EMAIL"},
            ).make

        dek = get_dek()
        now = datetime.now(UTC)
        try:
            user = await self.repo.create(
                org_id=None,
                role=UserRole.CITIZEN.value,
                name=encrypt_field(data.name, dek),
                name_hash=sha256_hash(data.name.lower()),
                email=encrypt_field(data.email, dek),
                email_hash=email_hash,
                phone=encrypt_field(data.phone, dek) if data.phone else None,
                phone_hash=sha256_hash(data.phone) if data.phone else None,
                password_hash=pwd_context.hash(data.password),
                is_active="1",
                created_at=now,
                updated_at=now,
            )
            await self.session.commit()
        except IntegrityError:
            # Race condition: a row with the same unique key (email_hash)
            # was inserted between the existence check and this commit.
            await self.session.rollback()
            return StandardResponse.conflict(
                message="Email already registered",
                data={"error": "DUPLICATE_EMAIL"},
            ).make
        except SQLAlchemyError:
            # Any other DB-level failure: roll back and return a clean error
            # without leaking the raw driver exception to the client.
            await self.session.rollback()
            return StandardResponse.internal_error(
                message="Registration failed due to a database error",
                data={"error": "DATABASE_ERROR"},
            ).make

        return StandardResponse.created(
            data={"id": user.id, "role": user.role},
            message="Registered successfully. Use POST /auth/token to login.",
        ).make

    async def bootstrap(self, data: BootstrapRequest) -> dict[str, Any]:
        count_result = await self.session.execute(
            select(func.count()).select_from(DpdpUser).where(
                DpdpUser.role == UserRole.SUPER_ADMIN.value
            )
        )
        if count_result.scalar_one() > 0:
            return StandardResponse.conflict(
                message="System already bootstrapped. A super admin already exists.",
                data={"error": "ALREADY_BOOTSTRAPPED"},
            ).make

        email_hash = sha256_hash(data.email.lower())
        existing = await self.repo.get_by_email_hash(email_hash)
        if existing:
            return StandardResponse.conflict(
                message="Email already registered",
                data={"error": "DUPLICATE_EMAIL"},
            ).make

        dek = get_dek()
        now = datetime.now(UTC)
        try:
            user = await self.repo.create(
                org_id=None,
                role=UserRole.SUPER_ADMIN.value,
                name=encrypt_field(data.name, dek),
                name_hash=sha256_hash(data.name.lower()),
                email=encrypt_field(data.email, dek),
                email_hash=email_hash,
                phone=None,
                phone_hash=None,
                password_hash=pwd_context.hash(data.password),
                is_active="1",
                created_at=now,
                updated_at=now,
            )
            await self.session.commit()
        except IntegrityError:
            # Race condition: another bootstrap/registration inserted a row
            # with the same unique key (email_hash) concurrently.
            await self.session.rollback()
            return StandardResponse.conflict(
                message="Email already registered",
                data={"error": "DUPLICATE_EMAIL"},
            ).make
        except SQLAlchemyError:
            # Any other DB-level failure: roll back and return a clean error
            # without leaking the raw driver exception to the client.
            await self.session.rollback()
            return StandardResponse.internal_error(
                message="Bootstrap failed due to a database error",
                data={"error": "DATABASE_ERROR"},
            ).make

        return StandardResponse.created(
            data={"id": user.id, "role": user.role},
            message="Super admin created. Use POST /auth/token to login, then POST /orgs to create your first org.",
        ).make

    def list_roles(self) -> dict[str, Any]:
        roles = []
        for role_enum, permissions in ROLE_PERMISSIONS.items():
            roles.append(
                {
                    "id": role_enum.value,
                    "name": role_enum.value.replace("_", " ").title(),
                    "permissions": [p.value for p in permissions],
                }
            )

        return StandardResponse.success(
            data={"roles": roles}, message="Roles retrieved successfully"
        ).make
