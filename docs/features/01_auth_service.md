# Auth Service — DPDP Consent Management

## Overview

The Auth Service manages JWT token lifecycle for DPDP consent management system. Provides OAuth 2.0-compliant token issuance (password and client_credentials grant types), refresh, revocation, introspection, and RBAC role discovery. Access tokens expire in 15 minutes; refresh tokens in 7 days. Revoked refresh tokens are tracked in-memory using jti (JWT ID) blacklist.

## DPDP Compliance

- **Clause**: §10 (Record Keeping & Accountability)
- Audit trail: token issuance/revocation logged for compliance
- Password hashing: Argon2 for secure credential storage

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| POST | `/v1/auth/token` | No | None | Issue access token via password or client_credentials grant |
| POST | `/v1/auth/refresh` | Yes (JWT) | None | Refresh expired access token |
| POST | `/v1/auth/revoke` | Yes (JWT) | None | Revoke refresh token (blacklist jti) |
| POST | `/v1/auth/introspect` | Yes (JWT) | INTROSPECT_TOKEN | Introspect token validity and permissions |
| GET | `/v1/auth/roles` | Yes (JWT) | MANAGE_RBAC_ROLES | List all RBAC roles and their permissions |

## Request / Response Examples

### POST /v1/auth/token

**Password Grant**

```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "username": "dpo@orgname.com",
    "password": "SecurePassword123"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900,
    "scope": "consent:read consent:write audit:read",
    "token_type": "Bearer"
  },
  "message": "Token issued successfully"
}
```

**Client Credentials Grant**

```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "dpdp-system",
    "client_secret": "dpdp-secret-change-me"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "",
    "expires_in": 900,
    "scope": "system:*",
    "token_type": "Bearer"
  },
  "message": "Token issued successfully"
}
```

### POST /v1/auth/refresh

```bash
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900,
    "scope": "consent:read consent:write audit:read",
    "token_type": "Bearer"
  },
  "message": "Token refreshed successfully"
}
```

### POST /v1/auth/revoke

```bash
curl -X POST http://localhost:8000/v1/auth/revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": null,
  "message": "Token revoked successfully"
}
```

### POST /v1/auth/introspect

```bash
curl -X POST http://localhost:8000/v1/auth/introspect \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "active": true,
    "scope": "consent:read consent:write audit:read",
    "sub": "550e8400-e29b-41d4-a716-446655440000",
    "exp": 1715948505
  },
  "message": "Token introspection successful"
}
```

### GET /v1/auth/roles

```bash
curl -X GET http://localhost:8000/v1/auth/roles \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "roles": [
      {
        "id": "super_admin",
        "name": "Super Admin",
        "permissions": ["consent:read", "consent:write", "audit:read", "rbac:manage"]
      },
      {
        "id": "org_admin",
        "name": "Org Admin",
        "permissions": ["consent:read", "consent:write", "audit:read"]
      },
      {
        "id": "dpo_reviewer",
        "name": "Dpo Reviewer",
        "permissions": ["form:review", "version:publish"]
      },
      {
        "id": "data_subject",
        "name": "Data Subject",
        "permissions": ["consent:withdraw", "data:export"]
      }
    ]
  },
  "message": "Roles retrieved successfully"
}
```

## Token Structure

### Access Token (HS256 JWT, 900 sec/15 min TTL)

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "role": "org_admin",
  "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "type": "access",
  "exp": 1715948505,
  "iat": 1715948405
}
```

### Refresh Token (HS256 JWT, 604800 sec/7 days TTL)

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "type": "refresh",
  "jti": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "exp": 1716553305,
  "iat": 1715948505
}
```

## Business Rules

1. **Grant Type Validation**: Only `password` and `client_credentials` grants are supported; other values return 400 `UNSUPPORTED_GRANT_TYPE`
2. **Password Verification**: Failed Argon2 hash verification returns 401 `INVALID_CREDENTIALS` (not distinguishing user existence for security)
3. **User Active Check**: Inactive users (is_active != "1") return 403 `USER_INACTIVE`
4. **Refresh Token Blacklist**: Revoked refresh tokens (tracked by jti) cannot be reused; reuse attempt returns 401 `TOKEN_REVOKED`
5. **Access Token Refresh**: Refresh endpoint renews access token; same refresh token may be reused across refreshes
6. **Expired Token Revoke**: Already-expired tokens can be revoked; returns 200 (idempotent)
7. **Introspection on Expired**: Expired tokens introspect as `active: false` with null scope/sub/exp

## Security Notes

- **Credential Storage**: Passwords hashed with Argon2 (CryptContext with deprecated="auto" mode)
- **Secret Key**: JWT signing uses `JWT_SECRET_KEY` env var (default: "consent-management-secret-change-me" — **must be changed in production**)
- **Algorithm**: HS256 (HMAC-SHA256) hardcoded
- **Token Blacklist**: In-memory set `_token_blacklist` — **not persistent across restart**; for production multi-instance deployments, move to Redis/database
- **Claims in Access Token**: Include `org_id` and `role` for authorization filters (consumer code checks these)
- **No Refresh Rotation**: Refresh tokens are **not** rotated; same token reusable for 7 days
- **System Service Grant**: client_credentials grant checks hardcoded `DPDP_CLIENT_ID` and `DPDP_CLIENT_SECRET` env vars; issues token with role `system_service`

## Audit Events

- `token_issued`: Implicitly logged when access token created (via user service login)
- `token_revoked`: Logged when refresh token blacklisted (audit_action = TOKEN_REVOKED)

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| UNSUPPORTED_GRANT_TYPE | 400 | grant_type not in {password, client_credentials} |
| MISSING_CREDENTIALS | 400 | username or password missing for password grant |
| MISSING_CLIENT_CREDENTIALS | 400 | client_id or client_secret missing for client_credentials grant |
| INVALID_CREDENTIALS | 401 | Email not found or password verification failed |
| INVALID_CLIENT | 401 | client_id or client_secret mismatch |
| USER_INACTIVE | 403 | User account disabled (is_active != "1") |
| USER_NOT_FOUND | 401 | Refresh attempt: user no longer exists |
| TOKEN_EXPIRED | 401 | Refresh token expired (exp check failed) |
| INVALID_SIGNATURE | 401 | JWT signature verification failed |
| DECODE_ERROR | 401 | JWT malformed or undecodable |
| INVALID_TOKEN_TYPE | 400 | Refresh endpoint received non-refresh token |
| TOKEN_REVOKED | 401 | Refresh token jti is in blacklist |
| TOKEN_GENERATION_FAILED | 500 | Unexpected error during jwt.encode() |
| INSUFFICIENT_SCOPE | 403 | Requester lacks Permission.INTROSPECT_TOKEN or Permission.MANAGE_RBAC_ROLES |

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| JWT_SECRET_KEY | consent-management-secret-change-me | HS256 signing secret |
| JWT_ALGORITHM | HS256 | Token signing algorithm |
| DPDP_CLIENT_ID | dpdp-system | System service client ID |
| DPDP_CLIENT_SECRET | dpdp-secret | System service client secret |

### Token TTLs

| Token Type | TTL | Value (sec) |
|-----------|-----|------------|
| ACCESS_TOKEN | 15 min | 900 |
| REFRESH_TOKEN | 7 days | 604800 |

## Notes

- Token blacklist is **in-memory only**; application restart clears revocations. For stateless deployments, integrate Redis or database-backed token revocation.
- Access tokens do not include jti; only refresh tokens are revoked (revoke endpoint checks `type == "refresh"` before blacklisting).
- Claims (sub, role, org_id) are accessible to downstream services; enforce authorization in individual endpoints using `require_permission()` decorator.
