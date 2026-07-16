# Architecture and Codebase Guide

This document explains how the EveryCRED DPDP Consent Management Backend is designed, why each technology was chosen, and how a new developer can navigate and extend the codebase. It is intended to be read before diving into any feature area.

## Overview

This service is a FastAPI microservice built to fulfil the compliance requirements of India's Digital Personal Data Protection Act 2023. It provides a structured platform for organisations to author consent forms, collect and manage citizen consent through a versioned form workflow, serve public-facing consent APIs authenticated by rotating API keys, and maintain a tamper-evident audit log of every consent lifecycle event. The architecture is deliberately layered: HTTP routing, business logic, data access, and persistence are each confined to their own layer, and no layer is allowed to bypass the one below it.

## Technology Choices

**FastAPI** was selected because async-native request handling is a hard requirement when a single service must concurrently handle dashboard calls from operators, real-time consent submissions from embedded SDKs, and background job polling — all without thread-pool exhaustion. FastAPI's dependency injection system also makes RBAC enforcement and database session lifecycle management composable and testable without framework magic.

**SQLAlchemy 2 async** provides an async ORM layer over MySQL without sacrificing the expressiveness of a full query builder. The 2.x series overhauled the async API to be truly non-blocking using `asyncio`, which pairs naturally with FastAPI's event loop. Using an ORM also means that Alembic can generate schema migrations by diffing ORM models against the live database, reducing the chance of human error in migration scripts.

**MySQL 8** is the chosen relational database because the compliance use case demands strong ACID guarantees, referential integrity, and reliable `utf8mb4` Unicode support for multilingual consent form content. MySQL 8 also supports `JSON` column types natively, which the service uses for storing consent purpose payloads and snapshot blobs without needing a separate document store.

**Redis** is used for tracking the state of asynchronous background jobs such as audit log exports, bulk reconsent operations, and notification dispatches. Rather than polling a database table, long-running operations write progress and results to Redis, keeping job-status reads fast and database writes minimal.

**Alembic** manages the database schema lifecycle. Migrations are stored as versioned Python scripts under `app/db/migrations/versions/` and are applied automatically at service startup when `RUN_MIGRATIONS_ON_STARTUP=true`. This means every deployment is self-healing with respect to schema drift.

**Poetry** manages dependencies and the virtual environment. The `poetry.lock` file pins every transitive dependency to an exact version, ensuring that local development, CI, and production all run the same dependency tree.

## Application Layers

When an HTTP request arrives, it passes through a well-defined sequence of layers before a response is sent back.

The request first enters the middleware stack. `RequestLoggingMiddleware` records the method, path, and timing of every request including CORS preflight calls. `CORSMiddleware` applies the configured allowed origins. `ErrorHandlerMiddleware` sits at the outermost position and catches any unhandled exception that escapes the route handler, converting it into a `StandardResponse` with an appropriate HTTP status code.

After the middleware stack, FastAPI resolves the matching route handler in `app/api/v1/routes/dpdp/`. Route handlers are thin by design. Their job is to parse the incoming HTTP body through a Pydantic schema (which enforces types and validation rules before the handler body runs), inject shared dependencies such as the database session and the authenticated user identity, call the appropriate service method, and wrap the result in a `StandardResponse`.

Service classes in `app/services/dpdp/` contain all business logic. A service method enforces RBAC permissions, orchestrates calls to one or more repositories, applies encryption or hashing where required, writes an audit log entry when a state-changing action occurs, and raises an `HTTPException` with a descriptive message when an expected failure condition is encountered.

Repositories in `app/repositories/` encapsulate all SQL. Each repository receives an `AsyncSession` injected from the FastAPI dependency and executes async SQLAlchemy queries against a specific ORM model. Services never write raw SQL, and repositories never contain business rules.

ORM models in `app/models/orm/` define the database schema. They are the single authoritative source of truth: Alembic reads them to generate migrations, and repositories query them. Pydantic schemas in `app/schemas/dpdp/` sit parallel to the ORM models and describe what the API accepts and returns, not what the database stores.

## Directory Structure

`app/` is the application package. Inside it, `api/` contains the FastAPI application factory and all routing. `core/` contains cross-cutting infrastructure — middleware, logging, CORS configuration, the standard response factory, RBAC logic, and the cryptographic utilities. `models/` holds both the ORM layer (`orm/`) and optional domain types (`domain/`). `repositories/` has one file per major ORM entity. `services/dpdp/` has one file per feature domain. `schemas/dpdp/` has one file per feature domain mirroring the service files. `db/` contains the Alembic environment and migration scripts.

`docs/` holds developer documentation including this file, `SETUP.md`, the API reference, database schema notes, and deployment guidance.

`tests/` contains pytest modules for the older CMP route surfaces as well as manual HTML test pages for the public consent flows. DPDP feature tests are written using `pytest-asyncio` with httpx's `AsyncClient`.

`nginx/` holds Nginx configuration intended for production deployments where the application sits behind a reverse proxy for TLS termination and static asset serving.

## Routing and API Versioning

All application routes live under the `/v1` prefix. The `create_v1_router()` function in `app/api/v1/router.py` constructs a single `APIRouter(prefix="/v1")` and then includes twelve sub-routers, one per feature domain. This is the single file where you can see the full topology of the API surface at a glance.

The routes are divided into two broad categories. The legacy CMP routes (auth, runtime sessions, SDK, templates, and credentials) existed before the DPDP feature set was added. The DPDP feature routes live entirely under `app/api/v1/routes/dpdp/` and cover organisations, users, forms, form versions, consents, public consent, reconsent, audit, analytics, notifications, and organisation API keys. The two categories coexist under the same `/v1` prefix without conflict.

## DPDP Feature Modules

### Authentication

The auth module at `/v1/auth` handles the full identity lifecycle: bootstrapping the first super-admin account, citizen self-registration, JWT token issuance and refresh, token revocation, and token introspection. The bootstrap endpoint is a one-time, unauthenticated operation that seeds the initial `super_admin` user and is idempotent once an account exists.

### Organisations

Organisation endpoints at `/v1/orgs` allow super-admins to create and manage data fiduciary organisations within the platform. Each organisation is the parent entity for forms, users, and API keys, and its settings govern defaults for consent expiry and notification behaviour.

### Users

User management at `/v1/users` supports creating operator accounts within an organisation and exposing DPDP data principal rights. Data principals (citizens) can retrieve their own consent history, request erasure of their personal data, request a data portability export, and register a nominee — all through endpoints gated by RBAC permissions that enforce the DPDP Act's individual rights provisions.

### Forms

The form module at `/v1/forms` manages the lifecycle of consent forms from draft through activation and deactivation. Forms are the top-level container; they hold metadata about the data fiduciary, the legal basis for collection, and the purpose categories being collected. An organisation can have multiple forms simultaneously active for different products or processing purposes.

### Versions

Every form has a version history managed at `/v1/forms/{form_id}/versions`. A version captures the actual consent notice content at a specific point in time. The workflow enforces a draft → in_review → active progression. A publisher submits a version for review, a DPO reviewer approves and publishes it, and the previous active version is automatically superseded. Rollback to a prior version is also supported.

### Consents

Consent records at `/v1/consents` are the core compliance artifact. Granting a consent produces a cryptographically signed receipt token. Each consent record captures the exact version of the form the data principal interacted with, the purposes accepted or declined, the channel, and a timestamp. Withdrawing a consent writes a new record marking the withdrawal rather than mutating the original row, preserving the full history.

### Public Consent

The public consent surface at `/v1/public` is intended for server-to-server calls from an organisation's own backend. Rather than a JWT, these endpoints authenticate via an `X-API-Key` header tied to an organisation API key. They provide unified accept, reconsent, status-check, and withdrawal operations designed for headless integration scenarios such as mobile SDKs or backend-triggered consent flows.

### Reconsent

The reconsent module at `/v1/reconsent` handles the situation where a new form version has been published and existing consents granted on the previous version are no longer current. It can identify which data principals need to re-consent, send notifications, and perform bulk revocation of stale consents — with a mandatory dry-run mode to preview the scope of a revocation before committing it.

### Audit

The audit log at `/v1/audit` is the compliance backbone of the platform. Every state-changing action in the system writes an immutable entry capturing who acted, what action was taken, the target entity, and a hash that chains each entry to the previous one, making the log tamper-evident. Audit entries can be listed with rich filtering and exported asynchronously for regulatory submission.

### Analytics

Analytics endpoints at `/v1/analytics` provide aggregate views over consent data: consent grant and withdrawal trends over a rolling date window, summary counts for an organisation, form distribution by status, and the top-performing forms by grant volume. These endpoints are read-only and scoped to users with the `VIEW_ANALYTICS` permission.

### Notifications

The notifications module at `/v1/notifications` handles outbound communication to data principals: expiry reminders sent before a consent is due to lapse, and preview-mode testing for notification templates. Notification dispatches run as background jobs and expose a job-status endpoint for polling.

### Organisation API Keys

API key management at `/v1/orgs/{org_id}-keys` allows organisation admins to create, list, and revoke the API keys used to authenticate public consent API calls. When a key is created, the raw plaintext is returned exactly once. Subsequent reads return only metadata. Keys are stored as SHA-256 hashes in the database.

## Authentication and Security

The service uses two distinct token types for two distinct caller contexts. Dashboard users (operators, DPOs, admins) authenticate with a long-lived JWT issued at `/v1/auth/token`, which encodes the user's identity and role. The SDK and public consent APIs use either short-lived session JWTs (backed by Redis for revocation) or organisation API keys verified against the `dpdp_org_api_keys` table.

RBAC is enforced through a permission-based model with seven distinct roles. `super_admin` has unrestricted access. `org_admin` can manage everything within their organisation but cannot create new organisations. `form_editor` can create and edit form drafts and submit them for review. `dpo_reviewer` can approve, publish, and view consents and audit data. `read_only_analyst` has read-only access to forms, consents, audit, and analytics. `citizen` can exercise their DPDP data principal rights and manage their own consents. `system_service` is for machine-to-machine calls — consent checking, bulk revocation, and notification dispatch. Each role maps to an explicit set of named permissions, and route handlers declare which permission they require using a dependency.

Sensitive personal data fields (names, email addresses, phone numbers) are encrypted at rest using AES-256-GCM via the `encrypt_field` utility in `app/core/security/crypto.py`. Each encrypted value includes a random 12-byte initialisation vector prepended to the ciphertext and authentication tag, then base64-encoded for storage. The Data Encryption Key is derived from `DPDP_DEK_HEX` at runtime.

IP addresses and user agent strings stored in consent records are hashed using SHA-256 with a daily rotating salt. This makes the stored values pseudonymous — they can be used to detect duplicate or anomalous submissions within a day without permanently storing PII.

Consent receipt tokens are HMAC-signed JWTs using the key from `DPDP_HMAC_KEY_HEX`. A recipient can verify the authenticity of a receipt without contacting the server, making them suitable for offline compliance verification.

## Database and ORM

The database layer uses SQLAlchemy 2's fully async session interface (`AsyncSession`) throughout. Sessions are created per-request via a FastAPI dependency that yields the session, commits on successful response, and rolls back on any exception. This ensures no partial writes leak into the database on handler errors.

Alembic migrations are stored in `app/db/migrations/versions/` as Python scripts. When `RUN_MIGRATIONS_ON_STARTUP=true`, the FastAPI lifespan event handler runs `alembic upgrade head` using the `alembic.ini` configuration at the project root before the server accepts any traffic. This guarantees that the schema is always in sync with the application code at deployment time.

The audit log is designed for immutability. Audit entries are append-only and linked by a hash chain where each row includes a hash of its own content combined with the previous entry's hash. Attempting to update or delete an audit row will be rejected at the ORM event listener level. Similarly, consent records are never mutated after creation — status changes such as withdrawal are modelled as new records, preserving the full provenance of every consent decision.

## Standard Response Format

Every endpoint in the service returns a JSON body in the same envelope shape:

```json
{
  "status": "success",
  "data": { ... },
  "message": "Human-readable description"
}
```

The `status` field is one of `"success"`, `"fail"`, or `"error"`. Successful 2xx responses use `"success"`. Client errors (4xx) use `"fail"`. Server errors (5xx) use `"error"`. This is implemented in `app/core/responses/standard_response.py` as the `StandardResponse` class with named factory classmethods: `success()`, `created()`, `bad_request()`, `unauthorized()`, `forbidden()`, `not_found()`, `conflict()`, `validation_error()`, and `internal_error()`. Every route handler calls one of these methods and returns the resulting `JSONResponse`. No route handler constructs a raw `dict` response.

This consistency means API consumers can always inspect the `status` field first, handle errors uniformly, and then descend into `data` only on success.

## Adding a New Feature

The process for adding a new feature is the same regardless of what the feature does, because the layers are consistent across the codebase.

Start with the **Pydantic schema** in `app/schemas/dpdp/`. Define a request body model, any path or query parameter models, and a response model. Keep schema classes focused and avoid putting business logic in validators.

Write the **service** class in `app/services/dpdp/`. The service method should accept the database session, the authenticated user identity, and the validated request data. It should enforce any RBAC requirement using the permission constants in `app/core/security/rbac.py`, call one or more repository methods, apply encryption if PII is involved, write an audit log entry for state-changing operations via `audit_writer`, and return either a data object or raise an `HTTPException`.

Write the **repository** method in `app/repositories/`. A repository method accepts an `AsyncSession` and executes one or more async SQLAlchemy statements. It should not contain any business logic and should not raise HTTP exceptions — it raises `sqlalchemy` exceptions which the service or middleware layer catches.

Write the **route handler** in `app/api/v1/routes/dpdp/`. Declare the HTTP method, path, and any path or query parameters. Inject the database session with `Depends(get_db_session)` and the authenticated identity with the appropriate auth dependency. Call the service method and return `StandardResponse.success(data=result).make`.

Finally, **register the router** in `app/api/v1/router.py` using `v1_router.include_router(your_router, prefix="/v1/your-prefix", tags=["Your Tag"])`. Once registered, the endpoint will appear in the OpenAPI docs at `/docs` on next server start.

If the feature requires new database columns or tables, create an Alembic migration:

```bash
alembic revision --autogenerate -m "add_your_table"
alembic upgrade head
```

Review the generated migration file before running it to ensure the autogenerate diff matches your intent, particularly around index creation and nullable constraints.
