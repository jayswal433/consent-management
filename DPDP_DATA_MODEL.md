# DPDP Data Model Reference

This document provides a complete reference of the DPDP data model, including all relationships, constraints, and field definitions.

## Entity Relationship Diagram

```
┌─────────────────┐
│      Org        │
└────────┬────────┘
         │ (1:N)
         │
    ┌────┴──────────────────────────────┐
    │                                   │
    ├────────────────────────────┐      │
    │                            │      │
┌───▼────────┐          ┌───────▼──────┐
│  DpdpUser  │          │ ConsentForm  │
└───┬────────┘          └───────┬──────┘
    │ (1:N)                     │ (1:N)
    │                           │
    │    ┌──────────────┐       │
    │    │              │       │
    │    │          ┌───▼──────────┐
    │    │          │ FormVersion  │
    │    │          └──────────────┘
    │    │
    │    ├────────────────────────────┐
    │    │                            │
    │    │                      ┌─────▼─────┐
    │    │                      │ DpdpConsent
    │    │                      └──────┬────┘
    │    │
┌───▼───────────┐
│  Nomination   │
└───────────────┘

    ┌────────────────────────────────────────┐
    │          AuditLog (append-only)        │
    │  (no updated_at, no soft delete)       │
    └────────────────────────────────────────┘

    ┌────────────────────────────────────────┐
    │  AsyncJob (for long-running ops)       │
    └────────────────────────────────────────┘
```

## Table Definitions

### dpdp_orgs
Organization/company that owns consent forms.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| name | VARCHAR(120) | UNIQUE, INDEX, NOT NULL | Organization name |
| short_code | VARCHAR(20) | UNIQUE, INDEX, NULL | Short identifier (e.g., "ACME") |
| color | VARCHAR(7) | NULL | Hex color code (e.g., "#FF5733") |
| role | VARCHAR(50) | NULL | Role/type (e.g., "data_fiduciary") |
| plan | VARCHAR(30) | NOT NULL, DEFAULT "free" | Subscription plan |
| dpo_name | TEXT | NULL | AES-256-GCM encrypted |
| dpo_email | TEXT | NULL | AES-256-GCM encrypted |
| dpo_email_hash | VARCHAR(64) | INDEX, NULL | SHA-256 hash for lookup |
| dpdp_reg_id | VARCHAR(50) | INDEX, NULL | Registration ID |
| status | VARCHAR(20) | INDEX, NOT NULL, DEFAULT "active" | active/inactive |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_orgs_name, idx_dpdp_orgs_status

---

### dpdp_users
Users in the system (staff and citizens).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| org_id | VARCHAR(36) | FK(dpdp_orgs), NULL, INDEX | NULL for citizens |
| role | VARCHAR(30) | INDEX, NOT NULL | UserRole enum value |
| name | TEXT | NOT NULL | AES-256-GCM encrypted |
| name_hash | VARCHAR(64) | INDEX, NOT NULL | SHA-256 hash |
| email | TEXT | NOT NULL | AES-256-GCM encrypted |
| email_hash | VARCHAR(64) | UNIQUE, INDEX, NOT NULL | SHA-256 hash (login lookup) |
| phone | TEXT | NULL | AES-256-GCM encrypted |
| phone_hash | VARCHAR(64) | INDEX, NULL | SHA-256 hash |
| initials | TEXT | NULL | AES-256-GCM encrypted |
| password_hash | VARCHAR(255) | NOT NULL | Argon2 hashed |
| is_active | VARCHAR(1) | NOT NULL, DEFAULT "1" | "1" or "0" |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_users_email_hash, idx_dpdp_users_role, idx_dpdp_users_org_id

**Foreign Keys:** org_id → dpdp_orgs.id (ON DELETE CASCADE)

**Unique Constraints:** email_hash

---

### dpdp_consent_forms
Consent form templates.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| org_id | VARCHAR(36) | FK(dpdp_orgs), INDEX, NOT NULL | Organization owner |
| name | VARCHAR(80) | INDEX, NOT NULL | Form name |
| code | VARCHAR(30) | UNIQUE, INDEX, NOT NULL | Uppercase unique code |
| owner | VARCHAR(100) | NULL | Owner name/identifier |
| purpose_short | VARCHAR(200) | NULL | Short purpose description |
| purpose | TEXT | NOT NULL | Full purpose statement |
| description | TEXT | NULL | Additional description |
| legal_basis | VARCHAR(30) | NULL | LegalBasis enum value |
| retention_days | VARCHAR(10) | NOT NULL, DEFAULT "365" | Data retention period |
| expiry_days | VARCHAR(10) | NOT NULL, DEFAULT "365" | Consent expiry period |
| third_parties | JSON | NULL | Array of third parties |
| user_rights | JSON | NULL | Array of user rights |
| data_fields | JSON | NULL | Array of data field definitions |
| status | VARCHAR(20) | INDEX, NOT NULL, DEFAULT "draft" | FormStatus enum |
| active_version | VARCHAR(10) | NULL | Current active version (e.g., "v1.0") |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_consent_forms_org_id, idx_dpdp_consent_forms_code, idx_dpdp_consent_forms_status

**Foreign Keys:** org_id → dpdp_orgs.id (ON DELETE CASCADE)

**Unique Constraints:** code

---

### dpdp_form_versions
Versioned iterations of consent forms.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| form_id | VARCHAR(36) | FK(dpdp_consent_forms), INDEX, NOT NULL | Parent form |
| version | VARCHAR(10) | NOT NULL | Version identifier (e.g., "v1.0") |
| status | VARCHAR(20) | INDEX, NOT NULL, DEFAULT "draft" | VersionStatus enum |
| title | VARCHAR(200) | NULL | Display title |
| description | TEXT | NULL | Version description |
| purpose | TEXT | NOT NULL | Full purpose statement |
| legal_basis | VARCHAR(30) | NOT NULL | LegalBasis enum value |
| retention_days | VARCHAR(10) | NOT NULL, DEFAULT "365" | Data retention |
| expiry_days | VARCHAR(10) | NOT NULL, DEFAULT "365" | Consent expiry |
| third_parties | JSON | NULL | Array of third parties |
| user_rights | JSON | NULL | Array of rights |
| data_fields | JSON | NULL | Array of field definitions |
| custom_body | TEXT | NULL | HTML/template body |
| reviewer_note | TEXT | NULL | DPO reviewer notes |
| reviewer_sign_off | VARCHAR(36) | NULL | Reviewer user ID |
| review_note | TEXT | NULL | Review comments |
| published_at | DATETIME | NULL | Publication timestamp |
| published_by | VARCHAR(36) | NULL | Publisher user ID |
| archived_at | DATETIME | NULL | Archive timestamp |
| submitted_at | DATETIME | NULL | Submission for review timestamp |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_form_versions_form_id, idx_dpdp_form_versions_status

**Foreign Keys:** form_id → dpdp_consent_forms.id (ON DELETE CASCADE)

**Unique Constraints:** (form_id, version)

---

### dpdp_consents
Individual consent records from citizens.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| user_id | VARCHAR(36) | FK(dpdp_users), INDEX, NOT NULL | Consenting user |
| form_id | VARCHAR(36) | FK(dpdp_consent_forms), INDEX, NOT NULL | Form granted |
| version | VARCHAR(10) | NOT NULL | Form version (e.g., "v1.0") |
| status | VARCHAR(20) | INDEX, NOT NULL, DEFAULT "granted" | ConsentStatus enum |
| optional_fields | TEXT | NULL | AES-256-GCM encrypted JSON |
| ip_hash | VARCHAR(64) | NULL | SHA-256 hash (never raw IP) |
| user_agent_hash | VARCHAR(64) | NULL | SHA-256 hash (never raw UA) |
| channel | VARCHAR(20) | NOT NULL | Channel enum (web/mobile) |
| granted_at | DATETIME | NULL | Consent grant timestamp |
| expires_at | DATETIME | INDEX, NULL | Consent expiry timestamp |
| withdrawn_at | DATETIME | NULL | Withdrawal timestamp |
| receipt_token | VARCHAR(512) | NULL | HMAC-SHA256 JWT receipt |
| withdrawal_receipt_id | VARCHAR(36) | NULL | Links to withdrawal record |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_consents_user_id, idx_dpdp_consents_form_id, idx_dpdp_consents_status, idx_dpdp_consents_expires_at

**Foreign Keys:** 
- user_id → dpdp_users.id (ON DELETE CASCADE)
- form_id → dpdp_consent_forms.id (ON DELETE CASCADE)

**Unique Constraints:** (user_id, form_id, version)

---

### dpdp_audit_log
Immutable audit log with hash chain.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| ts | DATETIME | INDEX, NOT NULL | Event timestamp |
| actor | VARCHAR(100) | INDEX, NOT NULL | User ID / admin ID / "system" |
| actor_type | VARCHAR(20) | INDEX, NOT NULL | ActorType enum (admin/user/system) |
| action | VARCHAR(50) | INDEX, NOT NULL | AuditAction enum value |
| target | VARCHAR(100) | INDEX, NULL | Resource ID (form/user/consent) |
| version | VARCHAR(10) | NULL | Version identifier |
| details | TEXT | NULL | Human-readable details |
| prev_hash | VARCHAR(64) | NULL | SHA-256 hash of previous entry |
| hash | VARCHAR(64) | NOT NULL | SHA-256 hash of this entry |
| org_id | VARCHAR(36) | INDEX, NULL | Organization context |

**Indexes:** idx_dpdp_audit_log_ts, idx_dpdp_audit_log_action, idx_dpdp_audit_log_actor, idx_dpdp_audit_log_org_id

**Special:** NO updated_at, NO soft delete, NO foreign keys (immutable)

**Hash Formula:**
```
hash = SHA256(id | ts | actor | action | target | details | prev_hash)
```

---

### dpdp_nominations
Nominee registration for data subject rights.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| user_id | VARCHAR(36) | FK(dpdp_users), INDEX, NOT NULL | Nominating user |
| nominee_name | TEXT | NOT NULL | AES-256-GCM encrypted |
| nominee_email | TEXT | NOT NULL | AES-256-GCM encrypted |
| nominee_email_hash | VARCHAR(64) | INDEX, NOT NULL | SHA-256 hash |
| nominee_phone | TEXT | NULL | AES-256-GCM encrypted |
| nominee_phone_hash | VARCHAR(64) | INDEX, NULL | SHA-256 hash |
| is_active | VARCHAR(1) | INDEX, NOT NULL, DEFAULT "1" | "1" or "0" |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_nominations_user_id, idx_dpdp_nominations_email_hash

**Foreign Keys:** user_id → dpdp_users.id (ON DELETE CASCADE)

---

### dpdp_async_jobs
Async job tracking for long-running operations.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | VARCHAR(36) | PK, INDEX | UUID |
| job_type | VARCHAR(30) | INDEX, NOT NULL | Job type (reconsent_notify/audit_export/portability_export) |
| status | VARCHAR(20) | INDEX, NOT NULL, DEFAULT "pending" | JobStatus enum |
| org_id | VARCHAR(36) | INDEX, NULL | Organization context |
| form_id | VARCHAR(36) | INDEX, NULL | Form context |
| initiated_by | VARCHAR(36) | NULL | User ID who initiated job |
| total | VARCHAR(10) | NOT NULL, DEFAULT "0" | Total items to process |
| processed | VARCHAR(10) | NOT NULL, DEFAULT "0" | Items processed |
| failed | VARCHAR(10) | NOT NULL, DEFAULT "0" | Items failed |
| result_url | TEXT | NULL | Signed download URL (expires) |
| result_url_expires_at | DATETIME | NULL | URL expiry timestamp |
| error_message | TEXT | NULL | Error details if failed |
| completed_at | DATETIME | NULL | Completion timestamp |
| created_at | DATETIME | NOT NULL | Timestamp |
| updated_at | DATETIME | NOT NULL | Timestamp |

**Indexes:** idx_dpdp_async_jobs_type, idx_dpdp_async_jobs_status, idx_dpdp_async_jobs_org_id

---

## Field Encryption Reference

### Fields that are AES-256-GCM Encrypted
- `dpdp_users.name`
- `dpdp_users.email`
- `dpdp_users.phone`
- `dpdp_users.initials`
- `dpdp_orgs.dpo_name`
- `dpdp_orgs.dpo_email`
- `dpdp_consents.optional_fields` (JSON)
- `dpdp_nominations.nominee_name`
- `dpdp_nominations.nominee_email`
- `dpdp_nominations.nominee_phone`

### Fields that are SHA-256 Hashed (for lookup)
- `dpdp_users.name_hash` (from name)
- `dpdp_users.email_hash` (from email, UNIQUE)
- `dpdp_users.phone_hash` (from phone)
- `dpdp_orgs.dpo_email_hash` (from dpo_email)
- `dpdp_consents.ip_hash` (from IP address)
- `dpdp_consents.user_agent_hash` (from User-Agent)
- `dpdp_nominations.nominee_email_hash` (from nominee_email)
- `dpdp_nominations.nominee_phone_hash` (from nominee_phone)

### Fields that are NEVER Stored Raw
- IP addresses (always hash)
- User agents (always hash)
- Passwords (always argon2)

## Constraint Summary

### Primary Keys
All tables use `VARCHAR(36)` UUID format for primary keys.

### Foreign Keys
- `dpdp_users.org_id` → `dpdp_orgs.id`
- `dpdp_consent_forms.org_id` → `dpdp_orgs.id`
- `dpdp_form_versions.form_id` → `dpdp_consent_forms.id`
- `dpdp_consents.user_id` → `dpdp_users.id`
- `dpdp_consents.form_id` → `dpdp_consent_forms.id`
- `dpdp_nominations.user_id` → `dpdp_users.id`

All foreign key relationships use `ON DELETE CASCADE`.

### Unique Constraints
- `dpdp_orgs.name`
- `dpdp_orgs.short_code`
- `dpdp_users.email_hash`
- `dpdp_consent_forms.code`
- `dpdp_form_versions.(form_id, version)`
- `dpdp_consents.(user_id, form_id, version)`

### Default Values
- `dpdp_orgs.plan` = "free"
- `dpdp_orgs.status` = "active"
- `dpdp_users.is_active` = "1"
- `dpdp_consent_forms.status` = "draft"
- `dpdp_consent_forms.retention_days` = "365"
- `dpdp_consent_forms.expiry_days` = "365"
- `dpdp_form_versions.status` = "draft"
- `dpdp_consents.status` = "granted"
- `dpdp_consents.channel` = "web" (or from request)
- `dpdp_nominations.is_active` = "1"
- `dpdp_async_jobs.status` = "pending"

## Timestamp Columns

All tables except `dpdp_audit_log` have:
- `created_at` — Set on record creation, never changes
- `updated_at` — Set on creation, updated on any modification

`dpdp_audit_log` has only:
- `ts` — Timestamp of the event (truly immutable)

## Indexing Strategy

**High-Priority Indexes (frequently queried):**
- `email_hash` columns (login lookups, unique)
- `org_id` columns (multi-tenant filtering)
- `status` columns (filtering by state)
- `form_id`, `user_id` (relationship navigation)

**Medium-Priority Indexes (analytical queries):**
- `ts` in audit_log
- `action` in audit_log
- `expires_at` in consents (for expiry cleanup)

**Low-Priority Indexes:**
- Single-field text searches (name_hash, code)

## Typical Query Patterns

### Find User by Email
```sql
SELECT * FROM dpdp_users WHERE email_hash = SHA256(?)
```

### Get Active Consents for User
```sql
SELECT * FROM dpdp_consents 
WHERE user_id = ? AND status = 'granted' 
ORDER BY granted_at DESC
```

### Get Expired Consents
```sql
SELECT * FROM dpdp_consents 
WHERE expires_at < NOW() AND status = 'granted'
```

### Audit Trail for Form
```sql
SELECT * FROM dpdp_audit_log 
WHERE target = ? AND action LIKE 'form_%'
ORDER BY ts DESC
```

### Verify Audit Chain
```sql
-- Get consecutive entries and verify:
-- current.prev_hash == previous.hash
SELECT id, hash, prev_hash FROM dpdp_audit_log 
ORDER BY ts ASC
```

---

**Data model is optimized for DPDP compliance, security, and performance.**
