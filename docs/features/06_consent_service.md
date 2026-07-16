# Consent Service

## Overview

The Consent Service is the core internal module responsible for managing the full lifecycle of a user's consent within the EveryCRED platform. It provides endpoints for granting consent to a specific form and version, checking whether a user currently holds valid consent, withdrawing or declining that consent, and retrieving cryptographically signed receipts as proof of consent. All endpoints are RBAC-protected and require a valid Bearer token issued to a platform user. The underlying data is stored in the `dpdp_consents` table and every state change produces a corresponding audit trail entry.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /v1/consents | Bearer | List consents with filters |
| POST | /v1/consents | Bearer | Grant consent |
| POST | /v1/consents/check | Bearer | Check consent status |
| GET | /v1/consents/{id} | Bearer | Get consent record |
| POST | /v1/consents/{id}/withdraw | Bearer | Withdraw consent |
| POST | /v1/consents/{id}/decline | Bearer | Decline (audit only, no record) |
| GET | /v1/consents/{id}/receipt | Bearer | Get HMAC-signed receipt |

## Granting Consent

When a platform user grants consent on behalf of a data principal, the service accepts the `user_id`, `form_id`, version string, an optional list of field names the user has consented to share, and the channel through which consent was collected.

### Grant Request

```json
{
  "user_id": "uuid",
  "form_id": "uuid",
  "version": "v1",
  "optional_fields": ["marketing", "analytics"],
  "channel": "web"
}
```

### Grant Response

```json
{
  "id": "uuid",
  "status": "granted",
  "granted_at": "2026-06-16T10:00:00Z",
  "expires_at": "2027-06-16T10:00:00Z",
  "receipt_token": "hmac-signed-token"
}
```

The response immediately returns a `receipt_token` that can be handed to the frontend or data principal as durable proof that consent was recorded at a specific point in time.

## Checking Consent

The check endpoint returns the current consent state for a given user and form without modifying any records. It is designed for services that need to gate behaviour behind a valid consent check before proceeding.

### Check Response

```json
{
  "has_consent": true,
  "version": "v1",
  "reconsent_required": false,
  "status": "granted"
}
```

The `reconsent_required` flag is `true` when the user holds a consent record but it was issued against an older form version than the one currently active. In that case the caller should prompt the user to re-consent before proceeding.

## Withdrawing Consent

Posting to `/{id}/withdraw` marks the consent record's status as `"withdrawn"` without deleting the underlying row. A new audit event is appended to the audit trail recording the timestamp, the requesting user, and the reason if provided. The response includes a `withdrawal_receipt_id` that can serve as a reference if the data principal later requests confirmation that their withdrawal was honoured.

## Declining Consent

The decline action is an audit-only operation. It records that a user was presented with a consent form and actively chose to decline rather than simply ignoring it, without creating a consent record of any kind. This distinction matters for compliance reporting because it documents informed refusal rather than a gap in the consent log.

## Receipts

The `receipt_token` is an HMAC-SHA256 signed payload encoding the fields `consent_id`, `user_id`, `form_id`, `version`, and `granted_at`. The signature is computed against the platform's secret key, making it tamper-evident. Frontends or data principals can store this token as portable proof of consent that can be verified later without querying the database directly. The GET `/{id}/receipt` endpoint regenerates and returns the signed token at any time while the consent remains active.

## Optional Fields

The `optional_fields` array lists the consent form fields that the user explicitly agreed to share beyond the mandatory minimum. Because these field names may constitute personal data in certain jurisdictions, they are stored in encrypted form. The encryption algorithm is AES-256-GCM using the key supplied in the `DPDP_DEK_HEX` environment variable. The service decrypts the value on read so callers always receive the plaintext list.

## Data Storage

The service applies several privacy-preserving transformations before writing to the database. The user's IP address is hashed using a daily rotating salt, so records cannot be reverse-engineered to reveal the original address and the salt rotation limits the window during which correlation is possible. The user agent string is similarly hashed. The `optional_fields` value is encrypted with AES-256-GCM as described above. Mandatory form field data and consent metadata such as status, timestamps, and version are stored in plaintext because they are required for compliance querying.
