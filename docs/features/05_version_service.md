# Version Service — DPDP Consent Management

## Overview

The Version Service manages full consent form versioning lifecycle with multi-stage review workflow. Versions follow status machine: draft → in_review → active, with ability to archive and rollback. Each version increments as major version (v1.0, v2.0, v3.0). DPO sign-off (reviewer_sign_off field) required to publish. Version diff endpoint compares data_fields between any two versions to highlight changes for reconsent workflows.

## DPDP Compliance

- **Clauses**: §6(1) (Consent Form), §6(2) (Material Changes Require Reconsent)
- Version tracking proves consent version at grant time for dispute resolution
- Diff endpoint enables detection of material changes (triggers reconsent)
- Audit trail: version_created, version_submitted, version_published, version_rollback logged
- Published versions immutable; changes require new draft

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/forms/{form_id}/versions` | Yes (JWT) | MANAGE_FORMS | List all versions for a form |
| POST | `/v1/forms/{form_id}/versions` | Yes (JWT) | MANAGE_FORMS | Create new draft version (one draft max) |
| PATCH | `/v1/forms/{form_id}/versions/{v}` | Yes (JWT) | MANAGE_FORMS | Update draft version |
| POST | `/v1/forms/{form_id}/versions/{v}/submit` | Yes (JWT) | MANAGE_FORMS | Submit version for review (draft → in_review) |
| POST | `/v1/forms/{form_id}/versions/{v}/publish` | Yes (JWT) | MANAGE_FORMS | Publish version with DPO sign-off (in_review → active) |
| POST | `/v1/forms/{form_id}/versions/{v}/rollback` | Yes (JWT) | MANAGE_FORMS | Rollback to archived version |
| GET | `/v1/forms/{form_id}/versions/diff` | Yes (JWT) | MANAGE_FORMS | Compare data_fields between two versions |

## Request / Response Examples

### POST /v1/forms/{form_id}/versions

```bash
curl -X POST http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "title": "Analytics Consent v2",
    "description": "Updated to include new data sources",
    "purpose": "To track user behavior on our website for improving user experience and service quality. Data will be anonymized after 90 days.",
    "legal_basis": "consent",
    "retention_days": 90,
    "expiry_days": 365,
    "third_parties": ["Google Analytics", "Hotjar", "Segment"],
    "user_rights": ["withdraw", "access", "portability"],
    "data_fields": [
      {"name": "browsing_history", "type": "string", "required": true},
      {"name": "device_info", "type": "string", "required": false},
      {"name": "user_preferences", "type": "object", "required": false}
    ],
    "custom_body": "<h2>Custom HTML body</h2>",
    "reviewer_note": "Please review new data sources before publishing"
  }'
```

**Response (201 Created)**

```json
{
  "status": 201,
  "data": {
    "id": "v2-uuid-12345",
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "status": "draft",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "Version created successfully"
}
```

### GET /v1/forms/{form_id}/versions

```bash
curl -X GET http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "versions": [
      {
        "id": "v1-uuid-12345",
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "version": "1.0",
        "status": "archived",
        "title": "Analytics Consent v1",
        "purpose": "To track user behavior...",
        "legal_basis": "consent",
        "retention_days": 90,
        "expiry_days": 365,
        "published_at": "2025-05-10T09:00:00Z",
        "published_by": "dpo-admin-id",
        "created_at": "2025-05-09T08:30:00Z"
      },
      {
        "id": "v2-uuid-12345",
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "version": "2.0",
        "status": "active",
        "title": "Analytics Consent v2",
        "purpose": "To track user behavior...",
        "legal_basis": "consent",
        "retention_days": 90,
        "expiry_days": 365,
        "published_at": "2025-05-22T10:45:00Z",
        "published_by": "dpo-admin-id",
        "created_at": "2025-05-22T10:30:00Z"
      }
    ],
    "total": 2
  },
  "message": "Versions retrieved successfully"
}
```

### POST /v1/forms/{form_id}/versions/{v}/submit

```bash
curl -X POST http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions/2.0/submit \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "reviewer_note": "Ready for DPO review. New Segment integration added."
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "v2-uuid-12345",
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "status": "in_review",
    "title": "Analytics Consent v2",
    "purpose": "To track user behavior...",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "Version submitted for review"
}
```

### POST /v1/forms/{form_id}/versions/{v}/publish

```bash
curl -X POST http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions/2.0/publish \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "reviewer_sign_off": "dpo-admin-id",
    "review_note": "Approved by DPO. No concerns."
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "v2-uuid-12345",
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "status": "active",
    "title": "Analytics Consent v2",
    "published_at": "2025-05-22T10:45:00Z",
    "published_by": "dpo-admin-id",
    "created_at": "2025-05-22T10:30:00Z"
  },
  "message": "Version published successfully"
}
```

### GET /v1/forms/{form_id}/versions/diff

```bash
curl -X GET "http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions/diff?from_version=1.0&to_version=2.0" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "from_version": "1.0",
    "to_version": "2.0",
    "added": [
      {
        "name": "user_preferences",
        "type": "object",
        "required": false
      }
    ],
    "removed": [],
    "changed": [
      {
        "field": "device_info",
        "from_value": {"name": "device_info", "type": "string", "required": true},
        "to_value": {"name": "device_info", "type": "string", "required": false}
      }
    ]
  },
  "message": "Diff retrieved successfully"
}
```

### POST /v1/forms/{form_id}/versions/{v}/rollback

```bash
curl -X POST http://localhost:8000/v1/forms/a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6/versions/2.0/rollback \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "reason": "Segment integration causes performance issues; reverting to v1.0"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "rolled_back_version": "2.0"
  },
  "message": "Version rolled back successfully"
}
```

## Business Rules

1. **One Draft at a Time**: Only one draft version allowed per form; creating new draft when one exists returns 409 `VERSION_DRAFT_EXISTS`
2. **Auto-Increment Versions**: Version strings auto-generated as v1.0, v2.0, v3.0 (major bumps only; no minor versions)
3. **Status Machine**:
   - draft: created; allows edits (PATCH); can be submitted
   - in_review: submitted; awaits DPO approval; can be published or discarded
   - active: published; immutable; one per form at a time
   - archived: previous active version; can be rolled back to
4. **DPO Sign-Off Required**: Publish requires reviewer_sign_off field (typically DPO admin user_id with DPO_REVIEWER role)
5. **Publish Side Effects**:
   - Previous active version archived
   - New version set as active
   - Form.active_version updated to new version string
   - Form status set to "active" (if was draft)
6. **Rollback Behavior**:
   - Only active versions can be rolled back
   - Most recent archived version becomes active
   - Current active version becomes archived
   - Form.active_version updated to restored version
7. **Immutable After Active**: Active versions cannot be edited; new draft required for changes
8. **Diff Comparison**: data_fields compared by field name; detects added, removed, changed fields; returns detailed before/after
9. **Edit Restrictions**: Only draft versions can be updated (PATCH); other statuses return 403 `CANNOT_EDIT_VERSION`

## Security Notes

- **Access Control**: All version operations require `MANAGE_FORMS` permission
- **DPO Sign-Off**: reviewer_sign_off field must be populated with authorized DPO user_id; no validation of actual role (enforced in route via Permission)
- **Audit Logging**: All mutations (create, update, submit, publish, rollback) logged with version string and reason
- **Data Fields Validation**: data_fields stored as JSON arrays; schema validation deferred to schema/pydantic level

## Audit Events

- **version_created**: Logged on POST /versions
  - Details: "Version {version} created"

- **version_updated**: Logged on PATCH /versions/{v}
  - Details: "Version {version} updated"

- **version_submitted**: Logged on POST /versions/{v}/submit
  - Details: "Version {version} submitted for review"

- **version_published**: Logged on POST /versions/{v}/publish
  - Details: "Version {version} published by {reviewer_sign_off}"

- **version_rollback**: Logged on POST /versions/{v}/rollback
  - Details: "Version {version} rolled back. Reason: {reason}"

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| FORM_NOT_FOUND | 404 | form_id does not exist |
| VERSION_NOT_FOUND | 404 | version string not found for form |
| VERSION_DRAFT_EXISTS | 409 | Draft version already exists for form |
| CANNOT_EDIT_VERSION | 403 | Attempted to edit non-draft version |
| VERSION_ALREADY_IN_REVIEW | 409 | Attempted to submit already in_review version |
| INVALID_VERSION_STATUS | 403 | Operation invalid for version status |
| PUBLISH_NOT_IN_REVIEW | 422 | Cannot publish version not in in_review status |

## Request Schema

### CreateVersionRequest

```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "purpose": "string (required, ≥30 chars)",
  "legal_basis": "consent | legitimate_interest | vital_interest (required)",
  "retention_days": "integer (1–1825, required)",
  "expiry_days": "integer (≥retention_days, required)",
  "third_parties": ["string (optional)"],
  "user_rights": ["string (optional)"],
  "data_fields": [
    {
      "name": "string",
      "type": "string",
      "required": "boolean"
    }
  ],
  "custom_body": "string (optional, HTML)",
  "reviewer_note": "string (optional)"
}
```

### UpdateVersionRequest

```json
{
  "title": "string (optional)",
  "description": "string (optional)",
  "purpose": "string (optional, ≥30 chars if provided)",
  "legal_basis": "string (optional)",
  "retention_days": "integer (optional)",
  "expiry_days": "integer (optional)",
  "third_parties": ["string (optional)"],
  "user_rights": ["string (optional)"],
  "data_fields": [array (optional)],
  "custom_body": "string (optional)"
}
```

### PublishVersionRequest

```json
{
  "reviewer_sign_off": "string (UUID, required, DPO admin user_id)",
  "review_note": "string (optional)"
}
```

### RollbackVersionRequest

```json
{
  "reason": "string (required, explanation for rollback)"
}
```

## Notes

- Version string format: "1.0", "2.0", "3.0" (major.minor where minor always 0)
- Versions allow independent field schema evolution; consumers compare versions to detect breaking changes
- Rollback implementation restores most recent archived version, not arbitrary version selection
- Diff endpoint useful for reconsent workflow: if material changes detected (added/removed critical fields), users must reconsent
- Published versions should be immutable in practice; updates require new draft workflow
