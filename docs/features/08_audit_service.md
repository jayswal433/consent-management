# Audit Service — DPDP Consent Management

## Overview

The Audit Service provides immutable, tamper-evident audit logging compliant with DPDP §10(d) requirements. Every audit entry contains SHA-256 hash chain (current entry hashes previous entry's hash) to detect tampering. Database access restricted to INSERT only (no UPDATE/DELETE). 7-year retention enforced; older entries archived to WORM (Write-Once-Read-Many) cold storage. Export endpoint generates async jobs for CSV/JSONL audit reports with signed download URLs.

## DPDP Compliance

- **Clause**: §10(d) (Audit Trail & Accountability Record)
- Hash chain: SHA-256(id || ts || actor || action || target || details || prev_hash) proves tamper-detection
- Append-only: DB user INSERT-only; no UPDATE/DELETE permissions
- 7-year retention: WORM cold storage after 2 years
- Export: Async export jobs for audit report generation

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/audit` | Yes (JWT) | MANAGE_AUDIT | List audit entries with filters and pagination |
| GET | `/v1/audit/{id}` | Yes (JWT) | MANAGE_AUDIT | Get single audit entry with prev_hash (for verification) |
| POST | `/v1/audit/export` | Yes (JWT) | MANAGE_AUDIT | Initiate async audit export job (CSV/JSONL) |
| GET | `/v1/audit/export/{id}` | Yes (JWT) | MANAGE_AUDIT | Get async export job status and download URL |

## Request / Response Examples

### GET /v1/audit

```bash
curl -X GET "http://localhost:8000/v1/audit?action=consent_granted&page=1&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "id": "audit-uuid-1",
        "ts": "2025-05-22T10:30:00Z",
        "actor": "550e8400-e29b-41d4-a716-446655440000",
        "actor_type": "user",
        "action": "consent_granted",
        "target": "550e8400-e29b-41d4-a716-446655440000",
        "version": "2.0",
        "details": "form_id=a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "hash": "sha256_hash_of_current_entry",
        "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
      },
      {
        "id": "audit-uuid-2",
        "ts": "2025-05-22T10:31:00Z",
        "actor": "550e8400-e29b-41d4-a716-446655440001",
        "actor_type": "user",
        "action": "consent_granted",
        "target": "550e8400-e29b-41d4-a716-446655440001",
        "version": "2.0",
        "details": "form_id=a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "hash": "sha256_hash_of_current_entry",
        "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 20
  },
  "message": "Audit logs retrieved successfully"
}
```

### GET /v1/audit/{id}

```bash
curl -X GET http://localhost:8000/v1/audit/audit-uuid-1 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "id": "audit-uuid-1",
    "ts": "2025-05-22T10:30:00Z",
    "actor": "550e8400-e29b-41d4-a716-446655440000",
    "actor_type": "user",
    "action": "consent_granted",
    "target": "550e8400-e29b-41d4-a716-446655440000",
    "version": "2.0",
    "details": "form_id=a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "hash": "sha256_hash_of_current_entry",
    "prev_hash": "sha256_hash_of_previous_entry",
    "org_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
  },
  "message": "Audit entry retrieved successfully"
}
```

### POST /v1/audit/export

```bash
curl -X POST http://localhost:8000/v1/audit/export \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "format": "csv",
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6"
  }'
```

**Response (202 Accepted)**

```json
{
  "status": 202,
  "data": {
    "job_id": "export-job-uuid-12345",
    "download_url": "/v1/audit/export/export-job-uuid-12345"
  },
  "message": "Audit export job accepted"
}
```

### GET /v1/audit/export/{id}

**Response (200 OK) — Running**

```json
{
  "status": 200,
  "data": {
    "job_id": "export-job-uuid-12345",
    "status": "running",
    "download_url": null,
    "completed_at": null,
    "error_message": null
  },
  "message": "Export job status retrieved"
}
```

**Response (200 OK) — Completed**

```json
{
  "status": 200,
  "data": {
    "job_id": "export-job-uuid-12345",
    "status": "completed",
    "download_url": "https://storage.example.com/exports/export-job-uuid-12345.csv?signature=...",
    "completed_at": "2025-05-22T11:00:00Z",
    "error_message": null
  },
  "message": "Export job status retrieved"
}
```

**Response (200 OK) — Failed**

```json
{
  "status": 200,
  "data": {
    "job_id": "export-job-uuid-12345",
    "status": "failed",
    "download_url": null,
    "completed_at": "2025-05-22T11:00:00Z",
    "error_message": "Insufficient disk space for export"
  },
  "message": "Export job status retrieved"
}
```

## Audit Entry Schema

### Fields

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique audit entry identifier |
| ts | ISO DateTime | Timestamp of event (UTC) |
| actor | String | User ID or system service ID performing action |
| actor_type | Enum | Type of actor (user, admin, system) |
| action | Enum | Action taken (see Audit Actions) |
| target | String | Resource ID being acted upon (user_id, form_id, etc.) |
| version | String | Relevant version string (e.g. "2.0" for version_published) |
| details | String | Contextual details (JSON or free text) |
| hash | SHA-256 | Current entry hash (for tamper detection) |
| prev_hash | SHA-256 | Previous entry hash (for chain continuity) |
| org_id | UUID | Organisation ID (for data residency/filtering) |

### Hash Computation

```
hash = SHA-256(id || ts || actor || action || target || details || prev_hash)
```

Verifier can recompute hash using all fields and compare to stored hash. If hashes don't match, entry has been tampered.

## Business Rules

1. **Append-Only**: Only INSERT operations allowed; no UPDATE/DELETE in production
2. **Hash Chain**: Every entry contains SHA-256 of current data + previous entry's hash; proof of chronological order
3. **7-Year Retention**: Entries older than 7 years archived to WORM storage
4. **2-Year Cold Archive**: After 2 years, entries moved to cold storage (slower access, lower cost)
5. **Export Format**: csv or jsonl only; invalid formats return 400 `INVALID_FORMAT`
6. **Async Export**: Returns job_id immediately (202 Accepted); consumer polls GET /export/{id} for status
7. **Signed Download URLs**: Export URLs include AWS S3 pre-signed signature; expire after time window
8. **Date Filtering**: from_date and to_date ISO datetime strings; validation returns 400 `INVALID_DATE_FORMAT` on parse failure
9. **Pagination**: page/limit required; invalid values silently clamped to defaults

## Audit Actions

| Action | Meaning | Typical Target | Details Payload |
|--------|---------|--------|---|
| consent_granted | User granted consent | user_id | form_id, version, channel |
| consent_withdrawn | User withdrew consent | user_id | form_id, version, reason |
| consent_declined | User declined consent | user_id | form_id, version |
| consent_expired | Consent auto-expired | user_id | form_id, version, old_version |
| version_published | Form version published | form_id | version, reviewer_sign_off, review_note |
| version_rollback | Form version rolled back | form_id | old_version, new_version, reason |
| version_submitted | Form version submitted for review | form_id | version, reviewer_note |
| form_created | Consent form created | form_id | form_name, code |
| form_deactivated | Consent form deactivated | form_id | reason, notify_dpo |
| form_activated | Consent form activated | form_id | — |
| org_created | Organisation created | org_id | org_name, short_code |
| org_offboarded | Organisation deleted/deactivated | org_id | reason |
| pii_erasure | User PII erased (Right to Erasure) | user_id | reason, affected_consents |
| key_rotation | Encryption key rotated | — | old_key_id, new_key_id, rotation_timestamp |
| export_requested | Data export (Right to Portability) initiated | user_id | format, export_id |
| reconsent_notified | User notified of reconsent requirement | user_id | form_id, version, job_id |
| auto_revoked | Consent auto-revoked (stale version) | user_id | form_id, older_than_date |
| security_event | Security incident or anomaly | — | event_type, severity, description |

## Security Notes

- **Access Control**: All audit endpoints require `MANAGE_AUDIT` permission
- **Hash Verification**: Consumer must recompute hash and compare to prev_hash to detect tampering
- **Immutability Enforcement**: DB role must have INSERT-only permission; no DELETE/UPDATE in production
- **Encryption at Rest**: Audit table encrypted at rest using DB-level or storage encryption (TDE)
- **Signed Export URLs**: Download URLs include time-bound AWS S3 pre-signed signature; expires after 1 hour
- **Confidentiality**: PII in audit details should be limited; use user_id instead of plaintext email

## Audit Events

The Audit Service **records** audit events but does not itself generate them. Service integrations (auth, consent, form, user) call `write_audit_entry()` to log events. Audit service provides read-only access (list, get, export).

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_DATE_FORMAT | 400 | from_date or to_date not valid ISO datetime |
| INVALID_FORMAT | 400 | export format not in {csv, jsonl} |
| AUDIT_NOT_FOUND | 404 | audit entry ID does not exist |
| JOB_NOT_FOUND | 404 | export job ID does not exist |

## Request Schema

### AuditListQuery

```json
{
  "actor_type": "user | admin | system (optional)",
  "action": "string (optional, e.g. 'consent_granted')",
  "form_id": "string (UUID, optional)",
  "user_id": "string (UUID, optional)",
  "from_date": "string (ISO datetime, optional)",
  "to_date": "string (ISO datetime, optional)",
  "page": "integer (default: 1)",
  "limit": "integer (default: 20)"
}
```

### AuditExportRequest

```json
{
  "format": "csv | jsonl (required)",
  "form_id": "string (UUID, optional, filters export to single form)"
}
```

## Notes

- Audit trail is the authoritative record of all system actions for compliance and dispute resolution
- Hash chain enables offline verification of integrity (no need to query database)
- Tamper detection: if recomputed hash != stored hash for any entry, audit log has been modified
- Export service generates signed download URLs for secure file delivery
- Retention policy (7 years) meets or exceeds most regulatory requirements (DPDP, GDPR, etc.)
- Consumer should periodically export and store offline copies for compliance audits
