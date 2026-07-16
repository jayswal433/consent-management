# User Service — DPDP Consent Management

## Overview

The User Service (Data Subject / Citizen) manages individual user profiles, consent history, and core DPDP data subject rights (Right to Erasure §13, Right to Portability §14, Right to Nominate §14). All PII fields (name, email, phone) are encrypted with AES-256-GCM and also hashed (SHA-256) separately for search/lookup. Citizens can only read their own data (enforced via JWT `sub` claim); admins can read all users. Erasure nullifies encrypted PII and withdraws all consents. Portability initiates async export job with signed download URL.

## DPDP Compliance

- **Clauses**: §11 (User Rights), §12 (Consent), §13 (Right to Erasure), §14 (Right to Portability/Nominatation)
- Encryption: Name, email, phone all AES-256-GCM encrypted; hashes for fast lookups
- Audit trail: pii_erasure, export_requested, nominee registration logged
- Erasure compliance: Null all PII; withdraw all consents; generate receipt_id

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/users` | Yes (JWT) | MANAGE_USERS | List users with pagination (filtered by org_id if present) |
| POST | `/v1/users` | Yes (JWT) | MANAGE_USERS | Create new user (citizen) with encrypted PII |
| GET | `/v1/users/{user_id}` | Yes (JWT) | MANAGE_USERS | Get user by ID; decrypt PII if self or super_admin |
| GET | `/v1/users/{user_id}/consents` | Yes (JWT) | MANAGE_USERS | List consents for user |
| GET | `/v1/users/{user_id}/rights` | Yes (JWT) | MANAGE_USERS | List available rights (withdraw, access, delete, portability, nominate) |
| POST | `/v1/users/{user_id}/rights/erasure` | Yes (JWT) | MANAGE_USERS | Right to Erasure: null PII, withdraw consents, generate receipt |
| POST | `/v1/users/{user_id}/rights/portability` | Yes (JWT) | MANAGE_USERS | Right to Portability: initiate async export job |
| POST | `/v1/users/{user_id}/nominee` | Yes (JWT) | MANAGE_USERS | Register nominee for data subject rights |

## Request / Response Examples

### POST /v1/users

```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "data_subject",
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "phone": "+91-9876543210",
    "password": "SecurePass123!"
  }'
```

**Response (201 Created)**

```json
{
  "status": 201,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "data_subject",
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "User created successfully"
}
```

### GET /v1/users/{user_id}

```bash
curl -X GET http://localhost:8000/v1/users/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK) — Self Access**

```json
{
  "status": 200,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "data_subject",
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "User retrieved successfully"
}
```

**Response (200 OK) — Admin Access (different user)**

```json
{
  "status": 200,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "role": "data_subject",
    "name": null,
    "email": null,
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "User retrieved successfully"
}
```

**Note**: Non-self, non-super-admin users cannot decrypt PII of other users

### GET /v1/users/{user_id}/consents

```bash
curl -X GET "http://localhost:8000/v1/users/550e8400-e29b-41d4-a716-446655440000/consents?status=granted" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "consents": [
      {
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "version": "1.0",
        "status": "granted",
        "granted_at": "2025-05-22T10:00:00Z",
        "expires_at": "2025-08-22T10:00:00Z"
      }
    ],
    "total": 1
  },
  "message": "User consents retrieved successfully"
}
```

### POST /v1/users/{user_id}/rights/erasure

```bash
curl -X POST http://localhost:8000/v1/users/550e8400-e29b-41d4-a716-446655440000/rights/erasure \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "reason": "User requested deletion due to privacy concerns"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "deleted": true,
    "affected_consents": 3,
    "erasure_receipt_id": "d9e8c7b6-a5f4-43c2-b1a0-9f8e7d6c5b4a"
  },
  "message": "User data erased successfully"
}
```

### POST /v1/users/{user_id}/rights/portability

```bash
curl -X POST http://localhost:8000/v1/users/550e8400-e29b-41d4-a716-446655440000/rights/portability \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "format": "json"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "download_url": "/v1/users/550e8400-e29b-41d4-a716-446655440000/data/export/c3b2a1f0-e9d8-47c6-b5a4-3f2e1d0c9b8a",
    "export_id": "c3b2a1f0-e9d8-47c6-b5a4-3f2e1d0c9b8a"
  },
  "message": "Data export initiated successfully"
}
```

### POST /v1/users/{user_id}/nominee

```bash
curl -X POST http://localhost:8000/v1/users/550e8400-e29b-41d4-a716-446655440000/nominee \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "nominee_name": "Bob Smith",
    "nominee_email": "bob.smith@example.com",
    "nominee_phone": "+91-9876543211"
  }'
```

**Response (201 Created)**

```json
{
  "status": 201,
  "data": {
    "nominee_id": "e4d3c2b1-a0f9-48d7-c6b5-4e3d2c1b0a9f",
    "created_at": "2025-05-22T10:45:00Z"
  },
  "message": "Nominee registered successfully"
}
```

## Business Rules

1. **Self-Access Only for Citizens**: Data subjects (JWT role = data_subject) can only access their own user record (requester_id == user_id); otherwise 403 `INSUFFICIENT_SCOPE`
2. **Admin Decryption**: Admins (super_admin) can decrypt any user's PII; other admins cannot
3. **Email Uniqueness**: Duplicate emails (via email_hash) return 409 `DUPLICATE_EMAIL`
4. **Password Hashing**: User passwords hashed with Argon2; plaintext never stored
5. **PII Encryption on Create**: name, email, phone immediately encrypted with AES-256-GCM; hash versions stored for searches
6. **Erasure Workflow**: 
   - All PII fields (name, email, phone, initials) set to NULL
   - name_hash and email_hash set to empty string hashes (sha256_hash(""))
   - is_active set to "0"
   - All user's consents status changed to "withdrawn"
   - Unique erasure_receipt_id generated for proof
7. **Portability Workflow**: No data modification; only creates async job and audit entry; download_url is relative path
8. **Nominee Phone Optional**: nominee_phone may be None; only encrypted if provided
9. **List Pagination**: Invalid page/limit return 400 `INVALID_PAGINATION`

## Security Notes

- **PII Storage**: name, email, phone encrypted with AES-256-GCM (DEK from `get_dek()`)
- **Search Hashes**: Separate SHA-256 hash stored for each encrypted field to enable queries like `WHERE email_hash = ?` without decryption
- **Erasure Safety**: PII fields nulled; user still retrievable by ID but with no personally identifiable information
- **Access Control**: 
  - Data subjects: self-access only
  - Admins: read-all; decrypt PII only if super_admin
  - System service: can read/decrypt all (for interop)
- **Nominee Encryption**: Nominee PII (name, email, phone) encrypted with same DEK; encrypted fields stored in nominations table
- **Decryption Errors**: Caught and silenced; PII returned as None on decrypt failure (avoids exposing crypto errors)

## Audit Events

- **pii_erasure**: Logged when user data erased
  - Actor: user_id (if self-initiated) or admin_id
  - ActorType: USER or ADMIN
  - Target: user_id being erased
  - Details: "Reason: ..."

- **export_requested**: Logged when portability export initiated
  - Actor: requester_id
  - ActorType: USER or ADMIN
  - Target: user_id
  - Details: "Format: {format}, Export ID: {export_id}"

- **nominee_registered**: (Implicit) logged when nominee created
  - Actor: requester_id (usually user_id)
  - ActorType: USER
  - Target: user_id
  - Details: "Nominee registered: {hashed_email_prefix}..."

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_PAGINATION | 400 | page < 1 or limit < 1 |
| DUPLICATE_EMAIL | 409 | Email already registered |
| USER_NOT_FOUND | 404 | user_id does not exist |
| INSUFFICIENT_SCOPE | 403 | Requester cannot access this user's data |
| DECRYPT_FAILED | 500 | AES-256-GCM decryption error (caught, silenced) |
| MISSING_DEK | 500 | DPDP_DEK_HEX env var not set |

## Request Schema

### DpdpUserCreateRequest

```json
{
  "org_id": "string (UUID, required)",
  "role": "string (required, e.g. 'data_subject')",
  "name": "string (required, encrypted)",
  "email": "string (required, email format, encrypted)",
  "phone": "string (optional, encrypted)",
  "password": "string (required, min 8 chars, hashed with Argon2)"
}
```

### ErasureRequest

```json
{
  "reason": "string (required, explanation for erasure)"
}
```

### PortabilityRequest

```json
{
  "format": "string (json | csv, required)"
}
```

### NomineeCreateRequest

```json
{
  "nominee_name": "string (required, encrypted)",
  "nominee_email": "string (required, email format, encrypted)",
  "nominee_phone": "string (optional, encrypted)"
}
```

## Notes

- Users created in this service are "Data Subjects" (citizens), separate from admin users created via admin service
- Encryption/decryption is automatic and transparent; consumers work with plaintext fields in responses
- Erasure is **not reversible**; consider implementing soft-delete with recovery period in future
- Portability export URL is signed for secure access; consumer must implement download endpoint with signature verification
- Nominee registration stores encrypted PII for future data subject rights delegation (§14 use case)
