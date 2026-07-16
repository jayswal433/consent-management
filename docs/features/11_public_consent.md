# Public Consent API

## Overview

External microservices — such as an authentication service, a mobile backend, or a partner integration layer — use the public consent endpoints to record and query consent on behalf of their users. Authentication is via the `X-API-Key` header carrying an organisation API key rather than a JWT, because these calls originate from server-to-server contexts where a human user session does not exist. The user is identified by an `external_user_id`, which is simply the UUID that the calling service uses internally to represent that person; no local EveryCRED account is required. The API key automatically scopes every operation to the organisation that issued it, so no organisation identifier needs to be included in the request body.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /v1/public/consents/accept | X-API-Key | Accept or automatically re-consent |
| POST | /v1/public/consents/reconsent | X-API-Key | Explicitly re-consent to a new version |
| GET | /v1/public/consents/status | X-API-Key | Check if user has valid consent |
| POST | /v1/public/consents/{id}/withdraw | X-API-Key | Withdraw a consent |

## Accepting Consent

The `POST /accept` endpoint is the primary entry point for external services. It is designed to be idempotent in intent: the calling service simply says "this user has accepted consent for this form" and the system determines the correct action based on what already exists in the database. Three distinct outcomes are possible.

If no prior consent record exists for that `external_user_id` and `form_id` combination, the system creates a fresh consent record and returns it with `reconsented: false`. If a consent record already exists and it was issued against the same form version that is currently active, the system returns a `409 Conflict` response to signal that the user has already consented and no action was taken. If a consent record exists but it was issued against an older form version than the one currently active, the old record is marked as superseded and a new consent record is created for the current version; the response carries `reconsented: true` and the `previous_consent_id` of the record that was replaced.

This means external services never need to check first and then decide whether to call an accept or a re-consent endpoint — a single call to `/accept` handles all three cases.

### Accept Request

```json
{
  "external_user_id": "user-uuid-from-your-service",
  "form_id": "form-uuid",
  "version": "v2",
  "optional_fields": ["marketing"]
}
```

The `version` field is optional. When omitted, the system uses the form's currently active version automatically, which is the recommended approach for most integrations because it removes the need for the calling service to know or track which version is active.

### Accept Response — Fresh Consent

```json
{
  "id": "consent-uuid",
  "status": "granted",
  "granted_at": "2026-06-16T10:00:00Z",
  "expires_at": "2027-06-16T10:00:00Z",
  "receipt_token": "hmac-token",
  "reconsented": false,
  "previous_consent_id": null
}
```

### Accept Response — Re-consent

```json
{
  "id": "new-consent-uuid",
  "status": "granted",
  "granted_at": "2026-06-16T10:00:00Z",
  "expires_at": "2027-06-16T10:00:00Z",
  "receipt_token": "hmac-token",
  "reconsented": true,
  "previous_consent_id": "old-consent-uuid"
}
```

## Checking Consent Status

The `GET /status` endpoint returns a simple boolean indicating whether the specified user currently holds active consent for the given form. A `true` status means the user has a consent record with status `"granted"` that targets the form's currently active version and has not expired. Every other situation — no record, wrong version, withdrawn, or expired — returns `false`. This design makes the endpoint easy to use as a gate check in middleware or service logic without additional null-handling.

### Status Response — True

```json
{
  "status": true,
  "consent_id": "uuid",
  "form_id": "uuid",
  "active_version": "v2",
  "user_consented_version": "v2",
  "granted_at": "2026-06-16T10:00:00Z",
  "expires_at": "2027-06-16T10:00:00Z"
}
```

### Status Response — False

```json
{
  "status": false,
  "consent_id": null,
  "form_id": "uuid",
  "active_version": "v2",
  "user_consented_version": null,
  "granted_at": null,
  "expires_at": null
}
```

When `status` is `false`, the `active_version` field still tells the caller which version the user would need to consent to, which can be useful for presenting the correct consent form on the calling service's side.

## Shadow Users

Because external users do not have EveryCRED accounts, the database cannot store a foreign key directly against a real user row. When an `external_user_id` is encountered for the first time, the system automatically creates a minimal record in the `dpdp_users` table — referred to as a shadow user — that satisfies the relational constraint without granting any platform access. Shadow users cannot authenticate against the dashboard or any internal API. Subsequent calls using the same `external_user_id` reuse the existing shadow record; a new shadow is never created for an `external_user_id` that has already been seen.

## Version Validation

When a `version` value is explicitly submitted with the request, the system validates it against the form's currently active version. If the submitted version does not match the active version, the request is rejected with a descriptive error message indicating which version is expected. This prevents a race condition where an external service might record consent against a version that has already been superseded. Omitting the `version` field entirely bypasses this concern because the system always resolves to the active version at the moment the request is processed.

## Webhook Events

When consent is accepted or re-consented, the system fires an asynchronous webhook to the organisation's configured webhook URL if one has been set. The payload includes the consent record, the event type, and the timestamp. The event type is `"consent.accepted"` for a fresh consent grant and `"consent.reconsented"` when an older record was superseded. Webhook delivery failures are logged but do not cause the API response to fail.
