# EveryCRED DPDP Consent Management — Database Reference

This document describes the database schema, migration strategy, encryption design, and immutability guarantees for the DPDP Consent Management Backend. The service uses MySQL 8 as its primary database, SQLAlchemy 2.x async ORM with the `aiomysql` driver, and Alembic for schema migrations.


## Connection Configuration

The database URL is resolved at startup in `app/core/config/database.py`. The service supports two configuration styles.

The first is a full connection URL, provided via the `DB_URL` or `DATABASE_URL` environment variable:

```
DB_URL=mysql+aiomysql://myuser:mypassword@db.host:3306/consent_db
```

The second is component-based configuration, where the URL is assembled from individual variables:

```
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=db.host
DB_PORT=3306
DB_NAME=consent_db
```

When both are present, `DB_URL` / `DATABASE_URL` takes precedence. The defaults — `root`, empty password, `localhost`, port `3306`, database `consent_db` — are suitable only for local development and must be overridden in any shared or production environment.

The engine is configured with async connection pooling via `create_async_engine`. Sessions are managed through `AsyncSession` with `expire_on_commit=False` to prevent lazy-load errors after commits in async context.

Migrations run automatically on application startup when `RUN_MIGRATIONS_ON_STARTUP=true` (the default). This calls `alembic upgrade head` programmatically before the first request is served. In production you may prefer to set this to `false` and run migrations as a separate deployment step.


## Core Tables

All primary keys are `VARCHAR(36)` UUID strings generated in application code before insert. All timestamps are stored as `DATETIME` in UTC without timezone offset.

### dpdp_orgs

Represents a tenant organisation — a Data Fiduciary under the DPDP Act. Each organisation has a designated Data Protection Officer (DPO), whose contact details are stored encrypted.

The table holds: `id` (UUID PK), `name` (the organisation display name, unique), `short_code` (short uppercase identifier, unique), `color` (optional brand color hex), `role` (e.g. `data_fiduciary`), `plan` (subscription tier, default `free`), `dpo_name` (AES-256-GCM encrypted), `dpo_email` (AES-256-GCM encrypted), `dpo_email_hash` (SHA-256 of plaintext email for equality lookups), `dpdp_reg_id` (optional registration identifier issued by the authority), `webhook_url` (optional callback URL for consent events), `status` (default `active`), `created_at`, and `updated_at`.

### dpdp_users

Represents both internal platform users (admins, DPO reviewers, form editors) and data subjects (citizens whose consent is being collected). When external applications call the public consent endpoints using `external_user_id`, the service creates a shadow user record transparently to maintain a consistent internal identity.

The table holds: `id` (UUID PK), `org_id` (FK to `dpdp_orgs`, nullable for unaffiliated citizens), `role` (one of `super_admin`, `org_admin`, `form_editor`, `dpo_reviewer`, `read_only_analyst`, `citizen`, `system_service`), `name` (AES-256-GCM encrypted), `name_hash` (SHA-256), `email` (AES-256-GCM encrypted), `email_hash` (SHA-256, **unique constraint**), `phone` (AES-256-GCM encrypted, nullable), `phone_hash` (SHA-256, nullable), `initials` (AES-256-GCM encrypted), `password_hash` (Argon2id), `is_active` (default `1`), `created_at`, and `updated_at`.

The `email_hash` unique constraint ensures no two accounts share the same email address, even though the email itself is encrypted and not directly searchable.

### dpdp_consent_forms

The master template definition for a consent form. A form is the named, versioned container for the legal text and configuration that governs consent collection. Its status lifecycle is `draft` → `active` → `deactivated` → `archived`.

The table holds: `id` (UUID PK), `org_id` (FK to `dpdp_orgs`), `name` (display name), `code` (uppercase alphanumeric + underscore identifier, **unique constraint**, used as a stable external reference), `owner` (email or team identifier), `purpose_short` (max 200 characters), `purpose` (full DPDP §6(1) compliant purpose statement, minimum 30 characters), `description` (optional longer description), `legal_basis` (one of `consent`, `legitimate_interest`, `vital_interest`), `retention_days` (default 365), `expiry_days` (default 365), `third_parties` (JSON array of third-party names), `user_rights` (JSON array of granted rights), `data_fields` (JSON array of collected field names), `status` (default `draft`), `active_version` (integer pointing to the currently published version number), `created_at`, and `updated_at`.

### dpdp_form_versions

Each form can have multiple versions. Versions are the unit of DPO review and publication. Only one version of a form may be in `active` status at a time. When a new version is published, the previous active version is archived, and consent holders on the old version are candidates for reconsent notification.

The table holds: `id` (UUID PK), `form_id` (FK to `dpdp_consent_forms`), `version` (integer, auto-incremented per form), `status` (default `draft`; lifecycle: `draft` → `in_review` → `active` → `archived`), `title`, `description`, `purpose`, `legal_basis`, `retention_days`, `expiry_days`, `third_parties` (JSON), `user_rights` (JSON), `data_fields` (JSON), `custom_body` (optional rich-text override for the consent UI), `reviewer_note` (note from the submitter to the DPO reviewer), `reviewer_sign_off` (DPO name recorded at publish time), `review_note` (DPO's notes at publish time), `published_at`, `published_by` (user ID), `archived_at`, `submitted_at`, `created_at`, and `updated_at`.

A unique constraint on `(form_id, version)` prevents duplicate version numbers per form.

### dpdp_consents

The consent ledger. Each row is an immutable record of a single consent event. Consents are never deleted or updated to correct their content — instead, a withdrawal creates a new `withdrawn_at` timestamp, and a version upgrade marks the old record as `superseded` while creating a new `granted` row.

The table holds: `id` (UUID PK), `user_id` (FK to `dpdp_users`), `form_id` (FK to `dpdp_consent_forms`), `version` (integer), `status` (default `granted`; values: `granted`, `withdrawn`, `declined`, `expired`, `superseded`), `optional_fields` (application-supplied extra data, stored AES-256-GCM encrypted as JSON), `ip_hash` (SHA-256 of the client IP with a daily salt), `user_agent_hash` (SHA-256 of the user agent string with a daily salt), `channel` (one of `web`, `mobile`, `api`), `granted_at`, `expires_at` (indexed for expiry-notification queries), `withdrawn_at`, `receipt_token` (HMAC-SHA256 signed JWT used as a portable consent proof), `withdrawal_receipt_id` (ID of the corresponding audit log entry for withdrawal), `created_at`, and `updated_at`.

A unique constraint on `(user_id, form_id, version)` prevents a user from having duplicate active consents for the same form version. The application enforces this constraint before inserting; a violation surfaces as a 409 Conflict.

### dpdp_audit_log

The tamper-evident event ledger. Every significant system action writes a row here. The table has no `updated_at` column, no soft-delete column, and no foreign key constraints by design — rows are never mutated after insertion.

The table holds: `id` (UUID PK), `ts` (timestamp of the event, indexed), `actor` (user ID or `system`), `actor_type` (one of `admin`, `user`, `system`), `action` (enum — see below), `target` (ID of the affected resource), `version` (version number if applicable), `details` (JSON with event-specific metadata), `prev_hash` (SHA-256 hash of the previous audit entry), `hash` (SHA-256 hash of this entry), and `org_id`.

Recorded action types include: `consent_granted`, `consent_withdrawn`, `consent_declined`, `consent_expired`, `consent_superseded`, `version_published`, `version_rollback`, `version_submitted`, `form_created`, `form_deactivated`, `form_activated`, `org_created`, `org_offboarded`, `pii_erasure`, `key_rotation`, `export_requested`, `reconsent_notified`, `auto_revoked`, `security_event`, `api_key_created`, and `api_key_revoked`.

### dpdp_org_api_keys

Stores the API keys used to authenticate public consent endpoint calls. Only the key's SHA-256 hash is persisted — the raw key is shown once at creation and never stored. The `key_prefix` is a short human-readable prefix (e.g., `ec_prod_`) stored in plaintext for identification in the UI.

The table holds: `id` (UUID PK), `org_id` (FK to `dpdp_orgs`), `label` (human-readable name), `key_prefix` (unique, plaintext), `key_hash` (SHA-256 of the raw key, unique), `is_active` (default `1`), `created_by` (user ID of the creator), `created_at`, `last_used_at` (updated asynchronously on each successful authentication), and `expires_at` (nullable; null means the key never expires).

### dpdp_nominations

Stores nominee records registered under DPDP Act §14, which allows a data subject to designate a person to exercise their rights after death or incapacity. All nominee PII is encrypted.

The table holds: `id` (UUID PK), `user_id` (FK to `dpdp_users`), `nominee_name` (AES-256-GCM encrypted), `nominee_email` (AES-256-GCM encrypted), `nominee_email_hash` (SHA-256), `nominee_phone` (AES-256-GCM encrypted, nullable), `nominee_phone_hash` (nullable), `is_active` (default `1`), `created_at`, and `updated_at`.

### dpdp_async_jobs

Tracks the state of background tasks — consent export jobs, reconsent notification batches, bulk-revoke operations, and audit exports. Callers receive a `job_id` immediately and poll this table via the relevant `GET .../jobs/{job_id}` endpoint.

The table holds: `id` (UUID PK), `job_type` (e.g., `notification`, `export`), `status` (default `pending`; values: `pending`, `running`, `completed`, `failed`), `org_id`, `form_id`, `initiated_by` (user ID), `total` (total items to process), `processed` (items processed so far), `failed` (items that errored), `result_url` (download URL once the job completes), `result_url_expires_at`, `error_message`, `completed_at`, `created_at`, and `updated_at`.


## Immutability Design

The `dpdp_audit_log` table is the system's source of truth for compliance purposes and is designed to be tamper-evident.

Every row carries a `hash` field computed as the SHA-256 digest of a canonical string composed of the entry's own fields concatenated in a fixed order:

```
hash = SHA256(id + ts + actor + action + target + details + prev_hash)
```

The `prev_hash` field on each row contains the hash of the row inserted immediately before it. This forms a hash chain: if any historical row is altered, its hash no longer matches the `prev_hash` stored in the row that follows it, and the chain breaks. Verification tooling can replay the chain from any starting point to confirm integrity.

Enforcement is purely at the application layer — the `audit_writer` module in `app/core/security/audit_writer.py` is the only code path that writes to this table, and it always reads the most recent row's hash before computing the new entry's hash. The table has no `UPDATE` permission granted to the application database user in production deployments.


## Encryption

The service uses AES-256-GCM authenticated encryption for all PII fields. The data encryption key (DEK) is a 32-byte key provided as 64 hex characters via the `DPDP_DEK_HEX` environment variable.

Each encrypted value is stored as a Base64-encoded blob in the format:

```
Base64( 12-byte IV || 16-byte GCM authentication tag || ciphertext )
```

The 12-byte IV is generated fresh for every encryption operation using a cryptographically secure random source. The GCM authentication tag provides integrity verification — if the ciphertext is tampered with, decryption fails with an authentication error rather than silently returning corrupted data.

Fields encrypted this way include `dpdp_users.name`, `dpdp_users.email`, `dpdp_users.phone`, `dpdp_users.initials`, `dpdp_orgs.dpo_name`, `dpdp_orgs.dpo_email`, `dpdp_nominations.nominee_name`, `dpdp_nominations.nominee_email`, `dpdp_nominations.nominee_phone`, and `dpdp_consents.optional_fields`.

For each encrypted field there is a corresponding `_hash` column that stores the SHA-256 digest of the plaintext. These hash columns are what the application queries when it needs equality lookups — for example, finding a user by email requires hashing the search email and querying `email_hash`, not decrypting every row.

IP addresses and user agent strings stored on consent records are also hashed, but with a daily rotating salt. This means the same IP on two different days produces different hashes, preventing long-term behavioural correlation while still allowing same-day deduplication detection. The salt is derived from the current UTC date and the `DPDP_DEK_HEX` key.

Consent receipt tokens are HMAC-SHA256 JWT signed with the key from `DPDP_HMAC_KEY_HEX`. Unlike the encryption key, this key is used only for signing — receipts are not encrypted, only authenticated.

Passwords are hashed using Argon2id, which is the current OWASP-recommended algorithm for password hashing.


## Running Migrations

Alembic is configured at the project root. The `alembic.ini` file points to `app/db/base` as the metadata source, and migrations are auto-generated by comparing the live SQLAlchemy models against the current database schema.

To apply all pending migrations:

```bash
alembic upgrade head
```

To generate a new migration after changing a model:

```bash
alembic revision --autogenerate -m "describe your change here"
```

Review the generated file in `alembic/versions/` before applying it. Auto-generated migrations are not always perfectly accurate — complex changes such as column renames, type changes requiring data transforms, or index alterations may need manual adjustment.

To roll back the most recently applied migration:

```bash
alembic downgrade -1
```

To roll back to a specific revision:

```bash
alembic downgrade <revision_id>
```

When `RUN_MIGRATIONS_ON_STARTUP=true`, the application calls `alembic upgrade head` programmatically during the lifespan startup event. This is convenient for development and single-instance deployments. In production deployments with multiple replicas or zero-downtime requirements, set this to `false` and run migrations as a pre-deployment step before rolling out the new application version.


## Key Constraints

The following unique and structural constraints are worth calling out explicitly because they affect application behaviour:

`dpdp_users.email_hash` has a unique constraint. Every user account must have a distinct email address. This is enforced via the hash, not the encrypted value, because the hash is the only searchable form.

`dpdp_consent_forms.code` has a unique constraint. The form code (e.g., `MARKETING_CONSENT_V1`) is a stable external identifier and must be unique across the entire system. It is used in public API calls via `form_code` query parameters.

`dpdp_form_versions.(form_id, version)` has a composite unique constraint. Version numbers are scoped to their parent form and may not be duplicated.

`dpdp_consents.(user_id, form_id, version)` has a composite unique constraint. A user may hold only one consent record per form per version. A conflict on this constraint means the user already has an active consent for that version, which surfaces as a 409 response. When a user re-consents to a newer version, the old row's status is updated to `superseded` before the new row is inserted, which releases the constraint on the new version tuple.

`dpdp_org_api_keys.key_hash` has a unique constraint. Since keys are hashed on arrival and compared by hash on every request, collisions would create authentication ambiguity. The unique constraint ensures each raw key maps to exactly one key record.
