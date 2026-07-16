# Organisation API Keys

## Overview

Organisations issue API keys to their backend services so those services can call the public consent endpoints without requiring a user session or JWT. Each API key is scoped to a single organisation; every public consent operation performed with that key is automatically attributed to the issuing organisation without requiring the caller to pass an organisation identifier separately. Security is a first-class concern in the key management design: the raw key value is returned only once at creation time and is never stored. Only the SHA-256 hash of the key is persisted in the database, which means a full database dump does not expose any usable credentials.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /v1/{org_id}-keys | Bearer | Create a new API key |
| GET | /v1/{org_id}-keys | Bearer | List API keys for the organisation |
| DELETE | /v1/{org_id}-keys/{key_id} | Bearer | Revoke a key |

All three management endpoints require a valid Bearer token from an authenticated platform user with sufficient permissions for the given organisation. The API keys themselves are used only on the public consent endpoints.

## Creating a Key

A new key is created by posting a human-readable name and an optional expiry timestamp. The name is a label for your own records — for example, distinguishing between your production backend and a staging environment.

### Create Request

```json
{
  "name": "Production Backend",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

If `expires_at` is omitted the key does not expire and remains valid until it is explicitly revoked. For long-lived integrations this is convenient, but for high-security environments it is better practice to set an expiry and rotate keys on a schedule.

### Create Response

```json
{
  "id": "uuid",
  "name": "Production Backend",
  "key": "ecm_live_abc123...xyz",
  "is_active": "1",
  "created_at": "2026-06-16T10:00:00Z",
  "expires_at": "2027-01-01T00:00:00Z"
}
```

The `key` field is present only in this creation response. Once this response is consumed the raw key cannot be retrieved again from any endpoint. Copy it immediately into your secrets manager or environment configuration.

## Using a Key

Pass the key in the `X-API-Key` request header when calling any public consent endpoint.

```
X-API-Key: ecm_live_abc123...xyz
```

The key prefix `ecm_live_` is a hint that helps identify EveryCRED API keys if they appear in logs or are accidentally included in a repository, making accidental exposure easier to detect and rotate.

## Key Validation

When a request arrives carrying an `X-API-Key` header, the server computes the SHA-256 hash of the submitted value and queries the database for a matching hash. It then checks that the key is active (`is_active = "1"`) and that the current timestamp has not passed the key's `expires_at` value. If all checks pass, the key's `last_used_at` timestamp is updated in the background so administrators can see when a key was last exercised without that update adding latency to the response.

## Listing and Revoking Keys

The list endpoint returns all keys belonging to the organisation along with their names, creation timestamps, last used timestamps, and expiry dates. The raw key value is never included in list responses — only metadata. To revoke a key, issue a DELETE request against the key's `{key_id}`. Revocation takes effect immediately; any in-flight requests using the revoked key will fail on their next validation check.

## Security Considerations

Store API keys in environment variables or a dedicated secrets manager such as HashiCorp Vault or AWS Secrets Manager. Keys must never be committed to version control, embedded in client-side code, or transmitted over unencrypted connections. Create separate keys for each environment — development, staging, and production — so that a key leaked from a lower environment cannot be used against production data. Revoke any key immediately if you suspect it has been compromised, then create a replacement. Auditing `last_used_at` regularly can help surface keys that are no longer in active use and should be retired.
