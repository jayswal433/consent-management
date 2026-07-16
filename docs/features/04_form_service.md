# Form Service — DPDP Consent Management

## Overview

The Form Service manages consent form template lifecycle and metadata. Provides CRUD operations for consent forms with status tracking (draft → active → deactivated). Forms define purpose, legal basis, data fields, retention, and expiry policies. Forms must have at least one published version before activation. Deletion is only allowed in draft status and only if no active consents exist. Deactivation stops new consents but preserves existing granted consents.

## DPDP Compliance

- **Clauses**: §6 (Consent Requirements), §7 (Consent Form Standards)
- Form purpose must be ≥30 characters (§6(1) requirement for specific purpose)
- Form code must be globally unique and uppercase
- Audit trail: form_created, form_updated, form_deleted, form_activated, form_deactivated
- Retention/expiry constraints: retentionDays 1–1825, expiryDays ≥ retentionDays

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/forms` | Yes (JWT) | MANAGE_FORMS | List forms with filters (status, owner, search, sort) |
| POST | `/v1/forms` | Yes (JWT) | MANAGE_FORMS | Create new form (status: draft) |
| GET | `/v1/forms/{form_id}` | Yes (JWT) | MANAGE_FORMS | Get form with versions and consent count |
| PATCH | `/v1/forms/{form_id}` | Yes (JWT) | MANAGE_FORMS | Update form details (owner, purpose_short) |
| DELETE | `/v1/forms/{form_id}` | Yes (JWT) | MANAGE_FORMS | Delete form (only if draft + no active consents) |
| POST | `/v1/forms/{form_id}/activate` | Yes (JWT) | MANAGE_FORMS | Activate form (requires active version) |
| POST | `/v1/forms/{form_id}/deactivate` | Yes (JWT) | MANAGE_FORMS | Deactivate form (stops new consents) |

## Request / Response Examples

### POST /v1/forms

```bash
curl -X POST http://localhost:8000/v1/forms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "name": "Website Analytics Consent",
    "code": "WEB_ANALYTICS",
    "owner": "analytics-team",
    "purpose_short": "Analytics tracking",
    "purpose": "To track user behavior on our website for improving user experience and service quality. Data will be anonymized after 90 days.",
    "description": "Detailed analytics consent form",
    "legal_basis": "consent",
    "retention_days": 90,
    "expiry_days": 365,
    "third_parties": ["Google Analytics", "Hotjar"],
    "user_rights": ["withdraw", "access", "portability"],
    "data_fields": [
      {"name": "browsing_history", "type": "string", "required": true},
      {"name": "device_info", "type": "string", "required": false}
    ]
  }'
```

**Response (201 Created)**

```json
{
  "status": 201,
  "data": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "code": "WEB_ANALYTICS",
    "status": "draft",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "Form created successfully"
}
```

### GET /v1/forms

```bash
curl -X GET "http://localhost:8000/v1/forms?status=active&owner=analytics-team&page=1&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "name": "Website Analytics Consent",
        "code": "WEB_ANALYTICS",
        "status": "active",
        "active_version": "1.0",
        "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "created_at": "2025-05-22T10:30:00Z",
        "consent_count": 1250
      }
    ],
    "total": 1,
    "page": 1,
    "limit": 20,
    "pages": 1
  },
  "message": "Forms retrieved successfully"
}
```

### GET /v1/forms/{form_id}

```bash
curl -X GET http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "name": "Website Analytics Consent",
    "code": "WEB_ANALYTICS",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "owner": "analytics-team",
    "status": "active",
    "active_version": "1.0",
    "purpose": "To track user behavior on our website for improving user experience and service quality. Data will be anonymized after 90 days.",
    "purpose_short": "Analytics tracking",
    "description": "Detailed analytics consent form",
    "legal_basis": "consent",
    "retention_days": 90,
    "expiry_days": 365,
    "third_parties": ["Google Analytics", "Hotjar"],
    "user_rights": ["withdraw", "access", "portability"],
    "data_fields": [
      {"name": "browsing_history", "type": "string", "required": true},
      {"name": "device_info", "type": "string", "required": false}
    ],
    "versions": [
      {
        "id": "v1-uuid",
        "version": "1.0",
        "status": "active"
      }
    ],
    "consent_count": 1250,
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T10:30:00Z"
  },
  "message": "Form retrieved successfully"
}
```

### PATCH /v1/forms/{form_id}

```bash
curl -X PATCH http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "owner": "product-analytics",
    "purpose_short": "Enhanced analytics tracking"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "name": "Website Analytics Consent",
    "code": "WEB_ANALYTICS",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "owner": "product-analytics",
    "status": "active",
    "active_version": "1.0",
    "purpose_short": "Enhanced analytics tracking",
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T11:00:00Z"
  },
  "message": "Form updated successfully"
}
```

### POST /v1/forms/{form_id}/deactivate

```bash
curl -X POST http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/deactivate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "reason": "Service discontinued for this use case",
    "notify_dpo": true
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "name": "Website Analytics Consent",
    "code": "WEB_ANALYTICS",
    "status": "deactivated",
    "active_version": "1.0",
    "created_at": "2025-05-22T10:30:00Z",
    "updated_at": "2025-05-22T11:15:00Z"
  },
  "message": "Form deactivated successfully"
}
```

## Business Rules

1. **Purpose Length**: purpose must be ≥30 characters (DPDP §6(1) specificity requirement)
2. **Code Uniqueness**: code must be globally unique (case-insensitive input, stored uppercase)
3. **Code Format**: Alphanumeric + underscore only; automatically uppercased
4. **Retention Constraints**: 
   - retentionDays: 1–1825 (5 years max)
   - expiryDays: must be ≥ retentionDays
5. **Draft-Only Creation**: New forms always created in draft status; cannot be activated until published
6. **Activation Guard**: Cannot activate if form.active_version is None (no version ever published)
7. **Deletion Guards**:
   - Only draft forms can be deleted
   - Cannot delete if form has active consents (status = "granted")
   - Error: 403 `FORM_HAS_ACTIVE_CONSENTS` if guard fails
8. **Deactivation Semantics**: Stops new consents; existing granted consents remain valid and honoured until expiry
9. **Status Machine**: 
   - draft → active (via activate endpoint + active version exists)
   - active ↔ deactivated (via deactivate/reactivate, not yet implemented)
10. **List Pagination**: page/limit must be ≥1; invalid values return 400

## Security Notes

- **Access Control**: All form operations require `MANAGE_FORMS` permission
- **Audit Logging**: All mutations (create, update, delete, activate, deactivate) logged with actor_id and reason
- **Consent Count Accuracy**: Consent count includes only status=granted records (not withdrawn/declined)
- **Data Fields Immutability**: data_fields stored as JSON; versions handle field schema changes (not mutable on form level)

## Audit Events

- **form_created**: Logged on POST /forms
  - Details: "Form created: {form.name}"

- **form_updated**: Logged on PATCH /forms/{id}
  - Details: "Form details updated"

- **form_deleted**: Logged on DELETE /forms/{id}
  - Details: "Form deleted"

- **form_activated**: Logged on POST /forms/{id}/activate
  - Details: "Form activated"

- **form_deactivated**: Logged on POST /forms/{id}/deactivate
  - Details: "Form deactivated. Reason: {reason}" + conditional " [DPO notified]"

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| DUPLICATE_FORM_CODE | 409 | code already exists |
| FORM_NOT_FOUND | 404 | form_id does not exist |
| FORM_HAS_ACTIVE_CONSENTS | 403 | Cannot delete form with granted consents |
| INVALID_FORM_STATUS | 403 | Operation invalid for current form status |
| FORM_NEVER_PUBLISHED | 403 | Cannot activate form without published version |

## Request Schema

### CreateFormRequest

```json
{
  "org_id": "string (UUID, required)",
  "name": "string (required)",
  "code": "string (required, unique, uppercase)",
  "owner": "string (required, team/owner name)",
  "purpose_short": "string (required, brief description)",
  "purpose": "string (required, ≥30 chars, detailed purpose per §6(1))",
  "description": "string (optional, long description)",
  "legal_basis": "consent | legitimate_interest | vital_interest (required)",
  "retention_days": "integer (1–1825, required)",
  "expiry_days": "integer (≥retention_days, required)",
  "third_parties": ["string (optional, list of processors)"],
  "user_rights": ["string (optional, e.g. 'withdraw', 'access', 'portability')"],
  "data_fields": [
    {
      "name": "string",
      "type": "string",
      "required": "boolean"
    }
  ]
}
```

### UpdateFormRequest

```json
{
  "owner": "string (optional)",
  "purpose_short": "string (optional)"
}
```

### DeactivateFormRequest

```json
{
  "reason": "string (required)",
  "notify_dpo": "boolean (default: false)"
}
```

## Notes

- Form code is the unique, human-readable identifier; form.id is UUID for internal use
- Purpose field enforces ≥30 characters to comply with DPDP §6(1) requirement for specificity
- Consent form itself (metadata) is separate from form versions (schema/content); versions handle actual consent language changes
- Deactivated forms can potentially be reactivated in future (status returned to active); implementation deferred
- List endpoint supports full-text search via `q` parameter and sorting by created_at, updated_at, name
