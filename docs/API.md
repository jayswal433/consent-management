# EveryCRED DPDP Consent Management — API Reference

This document covers every endpoint exposed by the DPDP Consent Management Backend. The service implements the Digital Personal Data Protection Act 2023 (DPDP Act) and provides consent lifecycle management, RBAC-protected administration, public-facing consent capture, audit logging, and analytics.

Base URL: `http://localhost:9000`

All responses are wrapped in a standard envelope:

```json
{
  "status": "success",
  "data": { ... },
  "message": "Human-readable description"
}
```

On errors the envelope is identical in shape, with `"status": "error"` and `data` containing any structured error detail.


## Authentication Overview

The API uses three distinct credential mechanisms depending on the calling context.

**Bearer JWT** is required for all administrative and internal endpoints. Tokens are obtained from `POST /v1/auth/token` and must be sent in the `Authorization: Bearer <token>` header. Access tokens expire after 1440 minutes (24 hours) by default. The JWT payload carries `sub` (user ID), `role`, and `org_id` claims, which drive RBAC enforcement.

**X-API-Key header** is used exclusively for the public consent endpoints at `/v1/public/consents/`. API keys are created per organisation through the org key management endpoints, stored as SHA-256 hashes, and identified by a short key prefix. Pass the raw key as `X-API-Key: <key>`.

**Legacy Bearer token** (password grant flow) is the same JWT mechanism — both `password` and `client_credentials` grant types are supported through `POST /v1/auth/token`.


## Auth — `/v1/auth`

These endpoints handle identity, token issuance, and RBAC role inspection. No authentication is required for bootstrap, register, or token unless noted.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/auth/bootstrap` | One-time super admin setup |
| POST | `/v1/auth/register` | Register a new citizen user |
| POST | `/v1/auth/token` | Obtain access and refresh tokens |
| POST | `/v1/auth/refresh` | Exchange refresh token for new access token |
| POST | `/v1/auth/revoke` | Revoke a refresh token |
| POST | `/v1/auth/introspect` | Inspect token claims and validity |
| GET | `/v1/auth/roles` | List all RBAC roles and their permissions |

### POST /v1/auth/bootstrap

Creates the initial `super_admin` account. This endpoint can only be called once; subsequent calls return a conflict error once a super admin exists.

```json
POST /v1/auth/bootstrap
Content-Type: application/json

{
  "name": "Platform Administrator",
  "email": "admin@example.com",
  "password": "StrongP@ssw0rd!"
}
```

### POST /v1/auth/token

Supports two grant types. Use `password` for human users and `client_credentials` for service-to-service calls.

```json
POST /v1/auth/token
Content-Type: application/json

{
  "grant_type": "password",
  "username": "admin@example.com",
  "password": "StrongP@ssw0rd!"
}
```

Successful response:

```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 86400,
    "token_type": "Bearer",
    "scope": "openid profile"
  },
  "message": "Token issued"
}
```

### POST /v1/auth/introspect

Requires `INTROSPECT_TOKEN` permission. Returns active status, scope, subject, and expiry of any token.

```json
POST /v1/auth/introspect
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```


## Organisations — `/v1/orgs`

Organisation endpoints manage the tenant layer. Each organisation has a DPO (Data Protection Officer) designation required for DPDP compliance. All four operations require JWT; creation and deletion require `CREATE_DELETE_ORG`, viewing requires `VIEW_ORG_PROFILE`, and updates require `UPDATE_ORG_SETTINGS`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/orgs` | List all organisations (paginated) |
| POST | `/v1/orgs` | Create a new organisation |
| GET | `/v1/orgs/{org_id}` | Retrieve organisation details |
| PATCH | `/v1/orgs/{org_id}` | Update org name, DPO info, plan, or webhook |

### POST /v1/orgs

```json
POST /v1/orgs
Authorization: Bearer <super_admin_token>
Content-Type: application/json

{
  "name": "Acme Corporation",
  "short_code": "ACME",
  "role": "data_fiduciary",
  "plan": "pro",
  "dpo_name": "Jane Doe",
  "dpo_email": "dpo@acme.com",
  "dpdp_reg_id": "DPDP-2024-001"
}
```


## Organisation API Keys — `/v1/orgs/{org_id}-keys`

API keys are org-scoped credentials used to authenticate public consent endpoints. The raw key is shown only at creation time — the backend stores only the SHA-256 hash. All three operations require `UPDATE_ORG_SETTINGS` permission.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/orgs/{org_id}-keys` | Create a new API key |
| GET | `/v1/orgs/{org_id}-keys` | List all API keys for the org |
| DELETE | `/v1/orgs/{org_id}-keys/{key_id}` | Revoke an API key |

### POST /v1/orgs/{org_id}-keys

```json
POST /v1/orgs/550e8400-e29b-41d4-a716-446655440000-keys
Authorization: Bearer <org_admin_token>
Content-Type: application/json

{
  "label": "Production Mobile App",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

Response includes the full raw key once — store it immediately:

```json
{
  "status": "success",
  "data": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "label": "Production Mobile App",
    "key_prefix": "ec_prod_",
    "raw_key": "ec_prod_a3f2b9d1...",
    "expires_at": "2026-12-31T23:59:59Z",
    "created_at": "2026-06-16T10:00:00Z"
  },
  "message": "API key created. Store the raw key — it will not be shown again."
}
```


## Users — `/v1/users`

User endpoints manage data subjects (citizens) and internal staff accounts. Sensitive fields (name, email, phone) are AES-256-GCM encrypted at rest. Most operations require JWT; the exact permission depends on whether the caller is acting on their own record or another user's.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/users` | List users (paginated, filterable by org) |
| POST | `/v1/users` | Register a user |
| GET | `/v1/users/{user_id}` | Retrieve user profile |
| GET | `/v1/users/{user_id}/consents` | List all consents for a user |
| GET | `/v1/users/{user_id}/rights` | List available DPDP rights for a user |
| POST | `/v1/users/{user_id}/rights/erasure` | Submit a right-to-erasure request |
| POST | `/v1/users/{user_id}/rights/portability` | Submit a data portability request |
| POST | `/v1/users/{user_id}/nominee` | Register a nominee (DPDP §14) |

### POST /v1/users/{user_id}/rights/erasure

Requires `ERASURE_REQUEST` permission.

```json
POST /v1/users/550e8400-e29b-41d4-a716-446655440001/rights/erasure
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "No longer wish to participate in the service",
  "request_id": "REQ-2026-001"
}
```

### POST /v1/users/{user_id}/nominee

Registers a nominee under DPDP Act §14. Nominee details are encrypted at rest.

```json
POST /v1/users/550e8400-e29b-41d4-a716-446655440001/nominee
Authorization: Bearer <token>
Content-Type: application/json

{
  "nominee_name": "Raj Kumar",
  "nominee_email": "raj.kumar@example.com",
  "nominee_phone": "+919876543210"
}
```


## Forms — `/v1/forms`

Consent forms are the templates from which consent collection is driven. Each form has a status lifecycle: `draft` → `active` → `deactivated` → `archived`. A form must have a published version before it can be activated.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/forms` | List forms (filter by status, owner, search query) |
| POST | `/v1/forms` | Create a new form draft |
| GET | `/v1/forms/{form_id}` | Retrieve form details |
| PATCH | `/v1/forms/{form_id}` | Update form metadata |
| DELETE | `/v1/forms/{form_id}` | Delete a draft form |
| POST | `/v1/forms/{form_id}/activate` | Activate a form |
| POST | `/v1/forms/{form_id}/deactivate` | Deactivate with notification option |
| GET | `/v1/forms/org/{org_id}/published` | List all published forms for an org |
| GET | `/v1/forms/org/{org_id}/latest-published` | Latest published form (public, no JWT required) |

### POST /v1/forms

Requires `CREATE_CONSENT_FORM` permission. The `purpose` field must be at least 30 characters, per DPDP Act §6(1). Both `retention_days` and `expiry_days` accept values between 1 and 1825, and `expiry_days` must be greater than or equal to `retention_days`.

```json
POST /v1/forms
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Marketing Communications Consent",
  "code": "MARKETING_CONSENT_V1",
  "org_id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "marketing-team@acme.com",
  "purpose_short": "Collect consent for marketing emails",
  "purpose": "We collect your personal data to send you marketing communications about our products and services in compliance with the Digital Personal Data Protection Act 2023.",
  "legal_basis": "consent",
  "retention_days": 365,
  "expiry_days": 365,
  "third_parties": ["Mailchimp", "Salesforce"],
  "user_rights": ["erasure", "portability", "correction"],
  "data_fields": ["email", "name", "preferences"]
}
```

### POST /v1/forms/{form_id}/deactivate

Requires `ACTIVATE_DEACTIVATE_FORM` permission.

```json
POST /v1/forms/550e8400-e29b-41d4-a716-446655440002/deactivate
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Product line discontinued",
  "notify_dpo": true
}
```


## Form Versions — `/v1/forms/{form_id}/versions`

Every form maintains a versioned history of its consent language and configuration. Versions follow a strict lifecycle: `draft` → `in_review` (via submit) → `active` (via publish). A published version becomes the form's `active_version`. Only one version may be active at a time. The diff endpoint enables side-by-side comparison of any two versions.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/forms/{form_id}/versions` | List all versions |
| POST | `/v1/forms/{form_id}/versions` | Create a new version draft |
| PATCH | `/v1/forms/{form_id}/versions/{version}` | Update a draft version |
| POST | `/v1/forms/{form_id}/versions/{version}/submit` | Submit for DPO review |
| POST | `/v1/forms/{form_id}/versions/{version}/publish` | Publish after review approval |
| POST | `/v1/forms/{form_id}/versions/{version}/rollback` | Rollback to this version |
| GET | `/v1/forms/{form_id}/versions/diff` | Compare two versions |

### POST /v1/forms/{form_id}/versions/{version}/submit

Requires `SUBMIT_FOR_REVIEW` permission.

```json
POST /v1/forms/550e8400-e29b-41d4-a716-446655440002/versions/2/submit
Authorization: Bearer <token>
Content-Type: application/json

{
  "reviewer_note": "Updated third-party disclosures per legal review"
}
```

### POST /v1/forms/{form_id}/versions/{version}/publish

Requires `APPROVE_PUBLISH_VERSION` permission. The reviewer must provide their sign-off name.

```json
POST /v1/forms/550e8400-e29b-41d4-a716-446655440002/versions/2/publish
Authorization: Bearer <token>
Content-Type: application/json

{
  "reviewer_sign_off": "Jane Doe (DPO)",
  "review_note": "Approved. Third-party disclosures are complete and accurate."
}
```

### POST /v1/forms/{form_id}/versions/{version}/rollback

Requires `ROLLBACK_VERSION` permission. The reason must be at least 10 characters.

```json
POST /v1/forms/550e8400-e29b-41d4-a716-446655440002/versions/1/rollback
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Version 2 contained an error in the third-party disclosures"
}
```

### GET /v1/forms/{form_id}/versions/diff

Query parameters: `from_version=1&to_version=2`. Returns a structured diff of all fields that changed between the two versions.


## Consents — `/v1/consents`

The consents endpoints provide internal, JWT-protected access to the consent ledger. These are intended for administrators, DPO reviewers, and internal services — not for end-user consent capture. Optional field data is stored AES-256-GCM encrypted. IP addresses and user agents are stored as salted SHA-256 hashes.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/consents` | Query consent records with filters |
| POST | `/v1/consents` | Grant consent on behalf of a user |
| POST | `/v1/consents/check` | Check whether a consent exists |
| GET | `/v1/consents/{consent_id}` | Retrieve a single consent record |
| POST | `/v1/consents/{consent_id}/withdraw` | Withdraw an active consent |
| POST | `/v1/consents/{consent_id}/decline` | Record an explicit decline (audit trail only) |
| GET | `/v1/consents/{consent_id}/receipt` | Download the HMAC-signed consent receipt |

### GET /v1/consents

Requires `VIEW_ALL_CONSENTS` permission. Supports filtering by `user_id`, `form_id`, `version`, `status`, `from_date`, and `to_date`, plus pagination via `page` and `limit`.

### POST /v1/consents

Requires `GRANT_CONSENT` permission. Used for backend-driven consent capture (e.g., importing existing consents).

```json
POST /v1/consents
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "version": 1,
  "optional_fields": { "preferred_language": "en", "marketing_channel": "email" },
  "channel": "api",
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 ..."
}
```

### GET /v1/consents/{consent_id}/receipt

Requires `DOWNLOAD_CONSENT_RECEIPT` permission. Returns an HMAC-SHA256-signed receipt JWT. Pass `?format=json` for a JSON representation or `?format=pdf` for a downloadable PDF.


## Public Consent — `/v1/public/consents`

These endpoints are the primary integration point for external applications. They are protected by `X-API-Key` rather than JWT. The API key determines which organisation the operation belongs to. External users are identified by `external_user_id`, which is mapped to an internal shadow user transparently.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/public/consents/accept` | Accept consent (handles fresh grant and version upgrade) |
| POST | `/v1/public/consents/reconsent` | Explicit reconsent for a new form version |
| GET | `/v1/public/consents/status` | Check current consent status |
| POST | `/v1/public/consents/{consent_id}/withdraw` | Withdraw a specific consent |

### POST /v1/public/consents/accept

This is the primary endpoint for consent capture. The logic is adaptive: if no prior consent exists for the user on this form, a fresh grant is created. If the user previously consented to an older version, the old consent is marked `superseded` and a new grant is recorded automatically. If the user already has an active grant on the current version, the call returns HTTP 409.

The `channel`, `user_agent`, and `ip_address` are derived automatically from the HTTP request if not explicitly provided. The `version` field is optional — if omitted, the form's current published version is used.

**Request:**

```json
POST /v1/public/consents/accept
X-API-Key: ec_prod_a3f2b9d1...
Content-Type: application/json

{
  "external_user_id": "user-abc-123",
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "version": 2,
  "optional_fields": {
    "language": "en",
    "source": "onboarding-flow"
  }
}
```

**Response (fresh grant):**

```json
{
  "status": "success",
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "status": "granted",
    "granted_at": "2026-06-16T10:30:00Z",
    "expires_at": "2027-06-16T10:30:00Z",
    "receipt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "reconsented": false,
    "previous_consent_id": null
  },
  "message": "Consent granted successfully"
}
```

**Response (version upgrade / reconsent):**

```json
{
  "status": "success",
  "data": {
    "id": "8d0f7780-8536-51ef-a55c-f18gd2g01bf8",
    "status": "granted",
    "granted_at": "2026-06-16T11:00:00Z",
    "expires_at": "2027-06-16T11:00:00Z",
    "receipt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "reconsented": true,
    "previous_consent_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  },
  "message": "Reconsent recorded. Previous consent superseded."
}
```

### GET /v1/public/consents/status

Query parameters: `external_user_id` (required) and `form_code` (optional; the form's unique uppercase code such as `MARKETING_CONSENT_V1`). Returns the current consent status for that user, scoped to the specific form when `form_code` is provided.

**Request:**

```
GET /v1/public/consents/status?external_user_id=user-abc-123&form_code=MARKETING_CONSENT_V1
X-API-Key: ec_prod_a3f2b9d1...
```

**Response (consented):**

```json
{
  "status": "success",
  "data": {
    "status": true,
    "consent_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "form_id": "550e8400-e29b-41d4-a716-446655440002",
    "active_version": 2,
    "user_consented_version": 2,
    "granted_at": "2026-06-16T10:30:00Z",
    "expires_at": "2027-06-16T10:30:00Z"
  },
  "message": "Consent status retrieved"
}
```

**Response (not consented):**

```json
{
  "status": "success",
  "data": {
    "status": false,
    "consent_id": null,
    "form_id": "550e8400-e29b-41d4-a716-446655440002",
    "active_version": 2,
    "user_consented_version": null,
    "granted_at": null,
    "expires_at": null
  },
  "message": "No active consent found"
}
```

### POST /v1/public/consents/reconsent

Explicitly re-collects consent when a form version has changed and the application wants to present updated terms before accepting them. Accepts `external_user_id`, `form_id`, `new_version`, optional `optional_fields`, `channel`, `user_agent`, and `ip_address`.

### POST /v1/public/consents/{consent_id}/withdraw

The caller must also pass `external_user_id` as a query parameter for identity verification. Accepts an optional `reason` and a required `channel`.

```json
POST /v1/public/consents/7c9e6679-7425-40de-944b-e07fc1f90ae7/withdraw?external_user_id=user-abc-123
X-API-Key: ec_prod_a3f2b9d1...
Content-Type: application/json

{
  "reason": "User opted out via account settings",
  "channel": "web"
}
```


## Reconsent — `/v1/reconsent`

These endpoints manage bulk reconsent workflows triggered when a form version changes and existing consent holders need to be notified and potentially re-enrolled.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/reconsent/pending` | List users whose consent is outdated for a form version |
| POST | `/v1/reconsent/notify` | Dispatch reconsent notifications |
| GET | `/v1/reconsent/jobs/{job_id}` | Poll background job status |
| POST | `/v1/reconsent/bulk-revoke` | Bulk-revoke stale consents |

### GET /v1/reconsent/pending

Requires `VIEW_ALL_CONSENTS`. The `form_id` query parameter is required. Returns paginated results.

### POST /v1/reconsent/notify

Requires `TRIGGER_NOTIFICATIONS`. Submits an asynchronous job to notify affected users. Supports `email`, `push`, and `sms` channels.

```json
POST /v1/reconsent/notify
Authorization: Bearer <token>
Content-Type: application/json

{
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "version": 3,
  "user_ids": ["550e8400-e29b-41d4-a716-446655440001"],
  "channel": "email"
}
```

### POST /v1/reconsent/bulk-revoke

Requires `BULK_REVOKE`. Pass `dry_run: true` to preview affected records without making changes.

```json
POST /v1/reconsent/bulk-revoke
Authorization: Bearer <token>
Content-Type: application/json

{
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "older_than": "2025-01-01T00:00:00Z",
  "dry_run": true
}
```


## Audit — `/v1/audit`

The audit log is append-only and tamper-evident through SHA-256 hash chaining. Every consent event, version lifecycle action, and administrative operation is recorded. Only `VIEW_AUDIT_LOG` and `EXPORT_AUDIT_LOG` permissions grant access.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/audit` | Query audit entries (filterable) |
| POST | `/v1/audit/export` | Start an async export job |
| GET | `/v1/audit/export/{job_id}` | Poll export job status |
| GET | `/v1/audit/{audit_id}` | Retrieve a single audit entry |

### GET /v1/audit

Filterable by `actor_type`, `action`, `form_id`, `user_id`, `from_date`, and `to_date`. Paginated via `page` and `limit`.

### POST /v1/audit/export

Triggers a background job that produces a downloadable export file. Use the returned `job_id` to poll for completion via `GET /v1/audit/export/{job_id}`.

```json
POST /v1/audit/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "from_date": "2026-01-01T00:00:00Z",
  "to_date": "2026-06-16T23:59:59Z",
  "format": "csv"
}
```


## Analytics — `/v1/analytics`

All analytics endpoints require `VIEW_ANALYTICS` permission and return aggregated, non-PII data.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/analytics/consent-trend` | Daily consent counts over a time window |
| GET | `/v1/analytics/summary` | KPI summary (total, active, withdrawn, expired) |
| GET | `/v1/analytics/forms-by-status` | Count of forms grouped by status |
| GET | `/v1/analytics/top-forms` | Top forms ranked by consent volume |

`GET /v1/analytics/consent-trend` accepts query parameters `days` (minimum 1, default 30) and an optional `form_id` to scope the trend to a single form. `GET /v1/analytics/summary` accepts optional `org_id`, `from_date`, and `to_date`. `GET /v1/analytics/top-forms` accepts `limit` (1–50, default 5) and an optional `org_id`.


## Notifications — `/v1/notifications`

Notification endpoints trigger background jobs that deliver messages to users via configurable channels. All require JWT.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/notifications/expiry-reminder` | Send consent expiry reminders |
| GET | `/v1/notifications/jobs/{job_id}` | Poll notification job status |
| POST | `/v1/notifications/test` | Send a test notification |

### POST /v1/notifications/expiry-reminder

Requires `TRIGGER_NOTIFICATIONS`. Targets consents expiring within the specified window.

```json
POST /v1/notifications/expiry-reminder
Authorization: Bearer <token>
Content-Type: application/json

{
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "within_days": 30,
  "channel": "email"
}
```

### POST /v1/notifications/test

Requires `APPROVE_PUBLISH_VERSION` permission. Useful for verifying notification template rendering before a production send.

```json
POST /v1/notifications/test
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "template": "expiry_reminder",
  "form_id": "550e8400-e29b-41d4-a716-446655440002",
  "version": 2
}
```


## Error Codes

All error responses use the same envelope with `"status": "error"`. The `message` field provides a human-readable explanation and the optional `data` field may contain structured error detail.

| HTTP Status | When It Occurs |
|-------------|---------------|
| 400 | Malformed request syntax or invalid parameter values |
| 401 | Missing or invalid credentials — error codes include `MISSING_CREDENTIALS`, `TOKEN_EXPIRED`, `INVALID_SIGNATURE`, `DECODE_ERROR`, `MISSING_API_KEY`, `INVALID_API_KEY`, `REVOKED_API_KEY`, `EXPIRED_API_KEY` |
| 403 | Authenticated but insufficient RBAC permissions for the requested operation |
| 404 | Resource not found — user, form, consent, job, or audit entry does not exist |
| 409 | Conflict — e.g., user already has an active consent for this form version, form code already exists, or bootstrap has already been completed |
| 422 | Validation failure — request body fails schema validation; `data` contains per-field error detail |
| 500 | Unexpected server error — check server logs |

### Example 422 Response

```json
{
  "status": "error",
  "data": {
    "errors": [
      {
        "field": "purpose",
        "message": "String should have at least 30 characters"
      },
      {
        "field": "expiry_days",
        "message": "expiry_days must be greater than or equal to retention_days"
      }
    ]
  },
  "message": "Validation failed"
}
```

### Example 401 Response

```json
{
  "status": "error",
  "data": {
    "code": "TOKEN_EXPIRED",
    "detail": "The access token has expired. Please refresh."
  },
  "message": "Authentication failed"
}
```

### Example 409 Response

```json
{
  "status": "error",
  "data": {
    "code": "CONSENT_ALREADY_ACTIVE",
    "existing_consent_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
  },
  "message": "User already has an active consent for this form version"
}
```
