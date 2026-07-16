# Analytics Service — DPDP Consent Management

## Overview

The Analytics Service provides consent KPI dashboards and trend reporting without exposing any PII. Aggregates consent grants/withdrawals over configurable time windows, computes acceptance and withdrawal rates, detects pending re-consent users, and returns top-performing forms by consent adoption. All metrics are aggregate counts — no personally identifiable information in responses. Supports organisation-level filtering for multi-tenant deployments.

## DPDP Compliance

- **Clause**: §10 (Record Keeping & Accountability)
- Privacy-by-design: All responses aggregate-only; no PII exposed
- Audit trail: Analytics queries themselves are not logged (read-only, non-sensitive)

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| GET | `/v1/analytics/consent-trend` | Yes (JWT) | MANAGE_ANALYTICS | Daily consent grants/withdrawals for N days |
| GET | `/v1/analytics/summary` | Yes (JWT) | MANAGE_ANALYTICS | Summary statistics (total, rates, pending reconsent) |
| GET | `/v1/analytics/forms-by-status` | Yes (JWT) | MANAGE_ANALYTICS | Form count by status (donut chart data) |
| GET | `/v1/analytics/top-forms` | Yes (JWT) | MANAGE_ANALYTICS | Top N forms by consent grants with acceptance rates |

## Request / Response Examples

### GET /v1/analytics/consent-trend

```bash
curl -X GET "http://localhost:8000/v1/analytics/consent-trend?days=30&form_id=a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "date": "2025-04-22",
        "granted": 45,
        "withdrawn": 2
      },
      {
        "date": "2025-04-23",
        "granted": 52,
        "withdrawn": 3
      },
      {
        "date": "2025-04-24",
        "granted": 48,
        "withdrawn": 1
      },
      {
        "date": "2025-05-22",
        "granted": 67,
        "withdrawn": 5
      }
    ],
    "days": 30
  },
  "message": "Consent trend retrieved successfully"
}
```

### GET /v1/analytics/summary

```bash
curl -X GET "http://localhost:8000/v1/analytics/summary?org_id=f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "total_granted": 1500,
    "total_withdrawn": 45,
    "withdrawal_rate": 0.0286,
    "acceptance_rate": 0.9714,
    "pending_re_consent": 123
  },
  "message": "Consent summary retrieved successfully"
}
```

### GET /v1/analytics/forms-by-status

```bash
curl -X GET "http://localhost:8000/v1/analytics/forms-by-status?org_id=f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "active": 12,
    "draft": 3,
    "in_review": 1,
    "archived": 5,
    "deactivated": 2
  },
  "message": "Forms by status retrieved successfully"
}
```

### GET /v1/analytics/top-forms

```bash
curl -X GET "http://localhost:8000/v1/analytics/top-forms?limit=5&org_id=f47ac10b-58cc-4372-a567-0e02b2c3d479" \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "items": [
      {
        "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
        "name": "Website Analytics Consent",
        "granted": 450,
        "withdrawn": 12,
        "acceptance_rate": 0.9740
      },
      {
        "form_id": "b2c3d4e5-f6a7-48b9-c0d1-e2f3a4b5c6d7",
        "name": "Marketing Communications",
        "granted": 380,
        "withdrawn": 25,
        "acceptance_rate": 0.9383
      },
      {
        "form_id": "c3d4e5f6-a7b8-49ca-d1e2-f3a4b5c6d7e8",
        "name": "Product Feedback Survey",
        "granted": 250,
        "withdrawn": 8,
        "acceptance_rate": 0.9688
      },
      {
        "form_id": "d4e5f6a7-b8c9-4adb-e2f3-a4b5c6d7e8f9",
        "name": "Terms of Service",
        "granted": 1200,
        "withdrawn": 0,
        "acceptance_rate": 1.0
      },
      {
        "form_id": "e5f6a7b8-c9da-4bec-f3a4-b5c6d7e8f9a0",
        "name": "Privacy Policy",
        "granted": 1180,
        "withdrawn": 2,
        "acceptance_rate": 0.9983
      }
    ],
    "limit": 5
  },
  "message": "Top forms retrieved successfully"
}
```

## Business Rules

1. **Days Range**: consent-trend defaults to 30 days; must be positive integer
2. **Date Filtering**: from_date/to_date in summary filtered by created_at (not granted_at/withdrawn_at); ISO datetime strings
3. **Withdrawn Before Today**: withdrawn consents counted only if withdrawn_at >= since date
4. **Pending Reconsent**: Distinct user count where version != form.active_version AND status=granted
5. **Withdrawal Rate**: withdrawn / (granted + withdrawn); returns 0.0 if no consents
6. **Acceptance Rate**: granted / (granted + withdrawn); returns 0.0 if no consents
7. **Form Status Counts**: Query all statuses even if count is 0 (returns zero values for empty statuses)
8. **Top Forms Limit**: Default 5; max typically 100; ties broken by form ID alphabetical order
9. **Acceptance Rate Precision**: Rounded to 4 decimal places (e.g., 0.9714)
10. **Org Filter Optional**: Omitting org_id returns global statistics (all organisations)

## Security Notes

- **Access Control**: All analytics endpoints require `MANAGE_ANALYTICS` permission
- **No PII Exposure**: All responses are aggregate counts; no email, names, or personal identifiers
- **Read-Only**: Analytics service only queries; no mutations
- **Query Filtering**: Optional org_id filter restricts queries to single organisation (multi-tenant isolation)

## Metrics Definitions

| Metric | Formula | Use Case |
|--------|---------|----------|
| total_granted | COUNT(status=granted) | Total consent grants received |
| total_withdrawn | COUNT(status=withdrawn) | Total consent withdrawals |
| withdrawal_rate | withdrawn / (granted+withdrawn) | % of users withdrawing (churn indicator) |
| acceptance_rate | granted / (granted+withdrawn) | % of users accepting (KPI) |
| pending_re_consent | COUNT(DISTINCT user_id where version != active_version) | Users needing reconsent after form update |
| granted (per-form) | COUNT(form_id, status=granted) | Consent adoption by form |
| withdrawn (per-form) | COUNT(form_id, status=withdrawn) | Withdrawal rate by form |
| (per-form) acceptance_rate | granted / (granted+withdrawn) | Form-specific acceptance (quality indicator) |

## Response Schema

### ConsentTrendResponse

```json
{
  "items": [
    {
      "date": "YYYY-MM-DD",
      "granted": "integer",
      "withdrawn": "integer"
    }
  ],
  "days": "integer (days queried)"
}
```

### SummaryResponse

```json
{
  "total_granted": "integer",
  "total_withdrawn": "integer",
  "withdrawal_rate": "float (0.0–1.0, 4 decimals)",
  "acceptance_rate": "float (0.0–1.0, 4 decimals)",
  "pending_re_consent": "integer"
}
```

### FormsByStatusResponse

```json
{
  "active": "integer",
  "draft": "integer",
  "in_review": "integer",
  "archived": "integer",
  "deactivated": "integer"
}
```

### TopFormsResponse

```json
{
  "items": [
    {
      "form_id": "string (UUID)",
      "name": "string",
      "granted": "integer",
      "withdrawn": "integer",
      "acceptance_rate": "float (0.0–1.0, 4 decimals)"
    }
  ],
  "limit": "integer"
}
```

## Examples: Interpreting Metrics

### Scenario 1: High Withdrawal Rate

**Metric**: withdrawal_rate = 0.15 (15%)

**Interpretation**: 15% of users are withdrawing consent. Investigate:
- Is the form too intrusive? Review purpose/data fields
- Are terms unclear? Simplify language
- Is reconsent deadline too short? Extend period

**Action**: Review form; consider version update with simplified terms

### Scenario 2: Pending Reconsent Spike

**Metric**: pending_re_consent = 500 (form version updated)

**Interpretation**: 500 users have old consent version; new version published.

**Action**: Use reconsent-service to notify users; set deadline; bulk-revoke after deadline

### Scenario 3: Top Form Imbalance

**Metric**: Form A has 1200 granted (1.0 acceptance), Form B has 45 granted (0.5 acceptance)

**Interpretation**: Form B struggling with adoption. Could be:
- Complex/intrusive purpose
- Poor UI/UX in presentation
- Niche use case

**Action**: Review Form B purpose/fields; A/B test simpler version

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_DATE_FORMAT | 400 | from_date or to_date not valid ISO datetime |

## Query Parameters

### consent-trend

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| days | integer | 30 | Days lookback; must be positive |
| form_id | UUID | null | Optional: filter to single form |

### summary

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| org_id | UUID | null | Optional: filter to organisation |
| from_date | ISO datetime | null | Optional: start date for consent.created_at |
| to_date | ISO datetime | null | Optional: end date for consent.created_at |

### forms-by-status

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| org_id | UUID | null | Optional: filter to organisation |

### top-forms

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | integer | 5 | Number of top forms to return |
| org_id | UUID | null | Optional: filter to organisation |

## Notes

- Trend data includes dates with zero grants/withdrawals (0 value, not omitted)
- Forms with zero consents appear in top-forms with acceptance_rate = 0.0
- Metrics computed at query time; no caching (suitable for real-time dashboards)
- Date filters use created_at (consent creation time), not granted_at (for consistency)
- Withdrawal rate 1.0 means all consents have been withdrawn (unusual; indicates major issue or old data)
- Acceptance rate 1.0 means no withdrawals yet (normal for new forms)
