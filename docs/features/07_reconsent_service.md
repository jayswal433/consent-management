# Re-consent Service — DPDP Consent Management

## Overview

The Re-consent Service manages re-consent workflows when consent form versions change materially. Detects pending reconsent (users with older version consents than form's active_version), notifies users via async jobs, and bulk-revokes expired consents (with dry_run preview). Used to enforce DPDP §6(2) requirement that material changes to consent terms trigger re-grant.

## DPDP Compliance

- **Clause**: §6(2) (Material Changes Require Explicit Reconsent)
- Automatic detection: Flags users with stale versions when form updates
- Notification tracking: Audit log entry per notified user
- Bulk revocation: Transparent dry_run for admin preview before execution

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/reconsent/pending` | Yes (JWT) | MANAGE_CONSENTS | Get users with pending reconsent (version mismatch) |
| POST | `/v1/reconsent/notify` | Yes (JWT) | MANAGE_CONSENTS | Notify users about reconsent requirement (async job) |
| POST | `/v1/reconsent/bulk-revoke` | Yes (JWT) | MANAGE_CONSENTS | Bulk revoke stale consents (with dry_run option) |
| GET | `/v1/reconsent/jobs/{id}` | Yes (JWT) | MANAGE_CONSENTS | Get async job status (notification/revocation) |

## Request / Response Examples

### GET /v1/reconsent/pending

```bash
curl -X GET "http://localhost:8000/v1/reconsent/pending?form_id=a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6&page=1&limit=100" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "current_version": "1.0",
        "required_version": "2.0"
      },
      {
        "user_id": "550e8400-e29b-41d4-a716-446655440001",
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "current_version": "1.0",
        "required_version": "2.0"
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 100
  },
  "message": "Pending reconsent users retrieved successfully"
}
```

### POST /v1/reconsent/notify

```bash
curl -X POST http://localhost:8000/v1/reconsent/notify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "user_ids": null
  }'
```

**Response (202 Accepted)**

```json
{
  "status": 202,
  "data": {
    "notified": 2,
    "job_id": "job-uuid-12345"
  },
  "message": "Notification job accepted"
}
```

**With Explicit User List**

```bash
curl -X POST http://localhost:8000/v1/reconsent/notify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "user_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001"
    ]
  }'
```

**Response (202 Accepted)**

```json
{
  "status": 202,
  "data": {
    "notified": 2,
    "job_id": "job-uuid-12345"
  },
  "message": "Notification job accepted"
}
```

### POST /v1/reconsent/bulk-revoke

**Dry Run Preview**

```bash
curl -X POST http://localhost:8000/v1/reconsent/bulk-revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "older_than": "2025-05-15T00:00:00Z",
    "dry_run": true
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "revoked": 5,
    "dry_run": true,
    "affected_users": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002",
      "550e8400-e29b-41d4-a716-446655440003",
      "550e8400-e29b-41d4-a716-446655440004"
    ]
  },
  "message": "Bulk revoke preview (dry run) completed"
}
```

**Execute Revocation**

```bash
curl -X POST http://localhost:8000/v1/reconsent/bulk-revoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "older_than": "2025-05-15T00:00:00Z",
    "dry_run": false
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "revoked": 5,
    "dry_run": false,
    "affected_users": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001",
      "550e8400-e29b-41d4-a716-446655440002",
      "550e8400-e29b-41d4-a716-446655440003",
      "550e8400-e29b-41d4-a716-446655440004"
    ]
  },
  "message": "Bulk revoke completed"
}
```

### GET /v1/reconsent/jobs/{id}

```bash
curl -X GET http://localhost:8000/v1/reconsent/jobs/job-uuid-12345 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK) — Running**

```json
{
  "status": 200,
  "data": {
    "job_id": "job-uuid-12345",
    "status": "running",
    "notified": 0,
    "failed": 0,
    "completed_at": null
  },
  "message": "Job status retrieved"
}
```

**Response (200 OK) — Completed**

```json
{
  "status": 200,
  "data": {
    "job_id": "job-uuid-12345",
    "status": "completed",
    "notified": 2,
    "failed": 0,
    "completed_at": "2025-05-22T10:45:00Z"
  },
  "message": "Job status retrieved"
}
```

## Business Rules

1. **Pending Query**: Returns consents where user's consent.version != form.active_version AND status=granted
2. **Form Validation**: Both endpoints validate form_id exists; return 404 `FORM_NOT_FOUND` if missing
3. **Active Version Required**: Endpoints require form.active_version to be set; return error `NO_ACTIVE_VERSION` if null
4. **User List Defaulting**: If user_ids is None/empty, notify endpoint queries all pending reconsent users
5. **Async Job Creation**: Notify endpoint creates AsyncJob record with status=running; immediately transitions to completed
6. **Audit Per User**: Each notified user generates one audit_log entry (reconsent_notified action)
7. **Dry Run Non-Destructive**: dry_run=true returns count/affected_users without modifying database
8. **Bulk Revoke Semantics**: Sets stale consents status=expired (not withdrawn; different semantics)
9. **Older Than Filter**: Revokes consents with granted_at <= older_than datetime
10. **Stale = Version Mismatch + Deadline**: Consents older than deadline AND with version != active_version are targeted

## Security Notes

- **Access Control**: All endpoints require `MANAGE_CONSENTS` permission
- **Dry Run Safety**: Enables admin preview before destructive operation; strongly recommended before bulk-revoke
- **Job Idempotency**: Job IDs are unique; re-fetching same job_id returns same status
- **Audit Immutability**: All revocations logged with actor_id=system (auto-revoked action type)

## Audit Events

- **reconsent_notified**: Logged per notified user in notify endpoint
  - Actor: actor_id (admin initiating)
  - ActorType: ADMIN
  - Target: user_id being notified
  - Details: "form_id={form_id}, job_id={job_id}"

- **auto_revoked**: Logged per revoked consent in bulk-revoke (if dry_run=false)
  - Actor: system service ID or "system"
  - ActorType: SYSTEM
  - Target: user_id
  - Details: "form_id={form_id}, older_than={older_than.isoformat()}"

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| FORM_ID_REQUIRED | 400 | form_id is None (GET /pending requires form_id) |
| FORM_NOT_FOUND | 404 | form_id does not exist |
| NO_ACTIVE_VERSION | 400 | Form has no active version (active_version is None) |
| JOB_NOT_FOUND | 404 | job_id does not exist |

## Request Schema

### ReconsentPendingQuery

```json
{
  "form_id": "string (UUID, required)",
  "page": "integer (default: 1)",
  "limit": "integer (default: 20)"
}
```

### ReconsentNotifyRequest

```json
{
  "form_id": "string (UUID, required)",
  "version": "string (e.g. '2.0', required)",
  "user_ids": ["string (UUID)"] or null
}
```

### BulkRevokeRequest

```json
{
  "form_id": "string (UUID, required)",
  "older_than": "string (ISO datetime, required)",
  "dry_run": "boolean (default: false)"
}
```

## Response Schema

### ReconsentPendingResponse

```json
{
  "items": [
    {
      "user_id": "string (UUID)",
      "form_id": "string (UUID)",
      "current_version": "string",
      "required_version": "string"
    }
  ],
  "total": "integer",
  "page": "integer",
  "limit": "integer"
}
```

### ReconsentNotifyResponse

```json
{
  "notified": "integer (count of notified users)",
  "job_id": "string (UUID)"
}
```

### BulkRevokeResponse

```json
{
  "revoked": "integer (count of revoked consents)",
  "dry_run": "boolean",
  "affected_users": ["string (UUID)"]
}
```

### JobStatusResponse

```json
{
  "job_id": "string (UUID)",
  "status": "pending | running | completed | failed",
  "notified": "integer",
  "failed": "integer",
  "completed_at": "string (ISO datetime) | null"
}
```

## Notes

- Reconsent workflow typically: admin publishes new form version → versioning service archives old → detect pending users with GET /pending → notify with POST /notify → on deadline, bulk-revoke with POST /bulk-revoke
- Dry run strongly recommended before bulk-revoke to preview impact
- older_than parameter should be set to reconsent deadline (e.g., deadline_date.isoformat())
- Job status polling: consumer should poll GET /jobs/{id} until status != running
- affected_users list in revoke response lists distinct user IDs; multiple consents per user possible (different forms) but each user appears once
