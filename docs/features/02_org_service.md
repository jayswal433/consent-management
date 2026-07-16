# Organisation Service — DPDP Consent Management

## Overview

The Organisation Service manages Data Fiduciary (organisation) registration, lifecycle, and DPO contact information. Provides CRUD operations for organisations with encrypted PII storage (AES-256-GCM) for DPO name/email. Each organisation has a unique short_code (uppercase), name, plan tier, and registration ID for DPDP compliance. DPO email is dual-encrypted: AES-256-GCM for storage and SHA-256 hashed separately for fast lookup queries.

## DPDP Compliance

- **Clauses**: §2(i) (Data Fiduciary definition), §10 (Record Keeping & Accountability)
- Audit trail: org_created, org_offboarded events logged
- Encryption: DPO PII encrypted at rest using DPDP_DEK_HEX (Data Encryption Key)

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/orgs` | Yes (JWT) | MANAGE_ORGANISATION | List organisations with pagination |
| POST | `/v1/orgs` | Yes (JWT) | MANAGE_ORGANISATION | Create new organisation |
| GET | `/v1/orgs/{org_id}` | Yes (JWT) | MANAGE_ORGANISATION | Get organisation by ID (decrypts PII) |
| PATCH | `/v1/orgs/{org_id}` | Yes (JWT) | MANAGE_ORGANISATION | Update organisation details |

## Request / Response Examples

### POST /v1/orgs

```bash
curl -X POST http://localhost:8000/v1/orgs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "name": "Example Data Fiduciary Ltd.",
    "short_code": "EDF",
    "dpo_name": "Jane Smith",
    "dpo_email": "dpo@example-df.com",
    "dpdp_reg_id": "DFDP202401001",
    "plan": "pro",
    "color": "#FF5733",
    "role": "data_fiduciary"
  }'
```

**Response (201 Created)**

```json
{
  "status": 201,
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Example Data Fiduciary Ltd.",
    "short_code": "EDF",
    "dpo_name": "Jane Smith",
    "dpo_email": "dpo@example-df.com",
    "dpdp_reg_id": "DFDP202401001",
    "plan": "pro",
    "color": "#FF5733",
    "role": "data_fiduciary",
    "status": "active",
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T10:30:00Z"
  },
  "message": "Organization created successfully"
}
```

### GET /v1/orgs

```bash
curl -X GET "http://localhost:8000/v1/orgs?page=1&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "name": "Example Data Fiduciary Ltd.",
        "short_code": "EDF",
        "dpo_name": null,
        "dpo_email": null,
        "dpdp_reg_id": "DFDP202401001",
        "plan": "pro",
        "color": "#FF5733",
        "role": "data_fiduciary",
        "status": "active",
        "created_at": "2025-05-22T10:30:00Z",
        "updated_at": "2025-05-22T10:30:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20
  },
  "message": "Organizations retrieved successfully"
}
```

**Note**: List endpoint returns `dpo_name` and `dpo_email` as `null` (not decrypted for privacy)

### GET /v1/orgs/{org_id}

```bash
curl -X GET http://localhost:8000/v1/orgs/f47ac10b-58cc-4372-a567-0e02b2c3d479 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Example Data Fiduciary Ltd.",
    "short_code": "EDF",
    "dpo_name": "Jane Smith",
    "dpo_email": "dpo@example-df.com",
    "dpdp_reg_id": "DFDP202401001",
    "plan": "pro",
    "color": "#FF5733",
    "role": "data_fiduciary",
    "status": "active",
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T10:30:00Z"
  },
  "message": "Organization retrieved successfully"
}
```

### PATCH /v1/orgs/{org_id}

```bash
curl -X PATCH http://localhost:8000/v1/orgs/f47ac10b-58cc-4372-a567-0e02b2c3d479 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "dpo_name": "John Doe",
    "dpo_email": "john.doe@example-df.com",
    "plan": "enterprise"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Example Data Fiduciary Ltd.",
    "short_code": "EDF",
    "dpo_name": "John Doe",
    "dpo_email": "john.doe@example-df.com",
    "dpdp_reg_id": "DFDP202401001",
    "plan": "enterprise",
    "color": "#FF5733",
    "role": "data_fiduciary",
    "status": "active",
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T11:00:00Z"
  },
  "message": "Organization updated successfully"
}
```

## Business Rules

1. **Unique Organisation Name**: Duplicate names return 409 `DUPLICATE_ORG_NAME`
2. **Unique Short Code**: Codes must be globally unique and uppercase; duplicates return 409 `DUPLICATE_ORG_CODE`
3. **DPO Email Hash**: Both plaintext email and SHA-256 hash stored; hash enables fast lookup without decryption
4. **Plan Tiers**: free, pro, enterprise (enum validated at schema level)
5. **Status Lifecycle**: New orgs created as "active"; no explicit deactivate endpoint (soft-delete deferred)
6. **PATCH Idempotent**: Sending same values for name/dpo_email is safe; only updates if new value differs
7. **List Pagination**: page/limit must be ≥1; invalid values return 400 `INVALID_PAGINATION`

## Security Notes

- **PII Encryption**: dpo_name and dpo_email encrypted with AES-256-GCM using DEK from `get_dek()` function
- **Email Hashing**: Plaintext email also hashed (SHA-256) without salt for fast equality checks in queries
- **Encryption Key**: DPDP_DEK_HEX env var must be set; missing key causes runtime error in encrypt/decrypt
- **Decryption Failures**: Decrypt errors silently return `null` for dpo_name/dpo_email (avoid exposing decrypt errors)
- **Access Control**: All org endpoints require `MANAGE_ORGANISATION` permission; enforced via `@require_permission()` in routes

## Audit Events

- **org_created**: Logged when organisation created
  - Actor: admin user ID
  - Target: org.id
  - Details: null or empty

- **org_updated**: Logged when organisation patched
  - Actor: admin user ID
  - Target: org.id
  - Details: stringified list of updated field names (e.g., "['name', 'dpo_name', 'plan']")

- **org_offboarded**: (Future) logged on org deactivation/deletion

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_PAGINATION | 400 | page < 1 or limit < 1 |
| DUPLICATE_ORG_NAME | 409 | name already exists |
| DUPLICATE_ORG_CODE | 409 | short_code already exists |
| ORG_NOT_FOUND | 404 | org_id does not exist |
| DECRYPT_FAILED | 500 | AES-256-GCM decryption failed (caught and silenced) |
| MISSING_DEK | 500 | DPDP_DEK_HEX env var not set or invalid |

## Request Schema

### OrgCreateRequest

```json
{
  "name": "string (required, unique)",
  "short_code": "string (required, uppercase, unique)",
  "dpo_name": "string (required, encrypted)",
  "dpo_email": "string (required, email, encrypted)",
  "dpdp_reg_id": "string (required, DPDP registration ID)",
  "plan": "free | pro | enterprise (default: free)",
  "color": "string (optional, hex color code)",
  "role": "string (default: 'data_fiduciary')"
}
```

### OrgUpdateRequest

```json
{
  "name": "string (optional, unique)",
  "dpo_name": "string (optional, encrypted)",
  "dpo_email": "string (optional, email, encrypted)",
  "plan": "free | pro | enterprise (optional)",
  "color": "string (optional, hex color code)"
}
```

## Notes

- List endpoint does not decrypt PII fields (returns `null` for dpo_name/dpo_email) for privacy in multi-user contexts
- Single-org GET endpoint decrypts and returns plaintext DPO details for authorized admins
- Encryption/decryption is transparent to consumers; encryption key rotation is handled centrally via crypto module
- No explicit soft-delete; org status change is a future feature for handling compliance requests
