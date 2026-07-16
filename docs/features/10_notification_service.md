# Notification Service — DPDP Consent Management

## Overview

The Notification Service manages async notification delivery for consent expiry reminders and re-consent prompts. Finds consents expiring within N days for a given form; creates async job; notifies users via email/push/SMS channels. Notifications are delivered asynchronously; endpoint returns immediately with job_id for polling. Test endpoint generates preview HTML for QA/template validation.

## DPDP Compliance

- **Clause**: §6(3) (User Notification & Communication)
- Notification tracking: Async job with status polling
- Channel diversity: Email, push, SMS support (future: SMS integration)
- Audit logging: Notification sends logged to audit trail

## Endpoints

| Method | Path | Auth Required | Permission | Description |
|--------|------|---------------|-----------|-------------|
| POST | `/v1/notifications/expiry-reminder` | Yes (JWT) | MANAGE_NOTIFICATIONS | Trigger expiry reminder notifications (async job) |
| GET | `/v1/notifications/jobs/{id}` | Yes (JWT) | MANAGE_NOTIFICATIONS | Get async notification job status |
| POST | `/v1/notifications/test` | Yes (JWT) | MANAGE_NOTIFICATIONS | Send test notification (preview HTML) |

## Request / Response Examples

### POST /v1/notifications/expiry-reminder

```bash
curl -X POST http://localhost:8000/v1/notifications/expiry-reminder \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "within_days": 30,
    "channel": "email"
  }'
```

**Response (202 Accepted)**

```json
{
  "status": 202,
  "data": {
    "notified": 47,
    "job_id": "job-uuid-12345"
  },
  "message": "Notification job accepted"
}
```

### GET /v1/notifications/jobs/{id}

**Running**

```bash
curl -X GET http://localhost:8000/v1/notifications/jobs/job-uuid-12345 \
  -H "Authorization: Bearer <access_token>"
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "job_id": "job-uuid-12345",
    "status": "running",
    "notified": 0,
    "failed": 0,
    "completed_at": null,
    "error_message": null
  },
  "message": "Notification job status retrieved"
}
```

**Completed**

```json
{
  "status": 200,
  "data": {
    "job_id": "job-uuid-12345",
    "status": "completed",
    "notified": 47,
    "failed": 0,
    "completed_at": "2025-05-22T10:45:00Z",
    "error_message": null
  },
  "message": "Notification job status retrieved"
}
```

**Partial Failure**

```json
{
  "status": 200,
  "data": {
    "job_id": "job-uuid-12345",
    "status": "completed",
    "notified": 45,
    "failed": 2,
    "completed_at": "2025-05-22T10:45:00Z",
    "error_message": "2 notifications failed to send (invalid email addresses)"
  },
  "message": "Notification job status retrieved"
}
```

### POST /v1/notifications/test

```bash
curl -X POST http://localhost:8000/v1/notifications/test \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{
    "template": "expiry_reminder",
    "form_id": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
    "version": "2.0",
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

**Response (200 OK)**

```json
{
  "status": 200,
  "data": {
    "sent": true,
    "preview_html": "<html>\n<body style=\"font-family: Arial, sans-serif; color: #333;\">\n    <h2>Consent Expiry Reminder</h2>\n    <p>Your consent for form <strong>a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6</strong> (version 2.0) is expiring soon.</p>\n    <p>Please renew your consent to continue using our services.</p>\n    <a href=\"#\" style=\"background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;\">Renew Consent</a>\n    <p style=\"margin-top: 20px; font-size: 12px; color: #999;\">This is an automated message. Please do not reply.</p>\n</body>\n</html>"
  },
  "message": "Test notification sent successfully"
}
```

## Business Rules

1. **Channel Validation**: channel must be in {email, push, sms}; invalid channels return 400 `INVALID_CHANNEL`
2. **Expiry Window**: Finds consents where expires_at <= now + within_days AND expires_at > now (not yet expired)
3. **Form Validation**: form_id must exist; invalid form returns 404 `FORM_NOT_FOUND`
4. **Async Execution**: Endpoint returns job_id immediately (202 Accepted); notifications sent asynchronously
5. **Job Tracking**: Async job created with status=running; transitions to completed/failed after execution
6. **Notified Count**: Returns count of consents matching expiry criteria; actual delivery tracked separately
7. **Template Validation**: template must be in {expiry_reminder, reconsent_required}; invalid templates return 400 `INVALID_TEMPLATE`
8. **HTML Generation**: Hardcoded template HTML; future: support custom templates from database
9. **Test Notification**: No actual delivery; generates preview HTML only (not integrated with email/SMS yet)

## Security Notes

- **Access Control**: All notification endpoints require `MANAGE_NOTIFICATIONS` permission
- **Async Safety**: Job status tracking enables polling without blocking client
- **Template Isolation**: Test endpoint does not send actual notifications; safe for QA
- **Channel Flexibility**: Architecture supports email/push/SMS; implementation deferred (placeholder)

## Notification Templates

### expiry_reminder

Notifies users that their consent is expiring soon; prompts to renew.

**Placeholder HTML**:
```html
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Consent Expiry Reminder</h2>
    <p>Your consent for form <strong>{form_id}</strong> (version {version}) is expiring soon.</p>
    <p>Please renew your consent to continue using our services.</p>
    <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Renew Consent</a>
    <p style="margin-top: 20px; font-size: 12px; color: #999;">This is an automated message. Please do not reply.</p>
</body>
</html>
```

### reconsent_required

Notifies users that consent form has been updated; prompts to review and re-grant.

**Placeholder HTML**:
```html
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2>Consent Form Update</h2>
    <p>The consent form <strong>{form_id}</strong> (version {version}) has been updated.</p>
    <p>Please review the updated terms and provide your consent again.</p>
    <a href="#" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">Review & Reconsent</a>
    <p style="margin-top: 20px; font-size: 12px; color: #999;">This is an automated message. Please do not reply.</p>
</body>
</html>
```

## Audit Events

- **reconsent_notified**: Logged when expiry reminder sent
  - Actor: actor_id (admin initiating)
  - ActorType: ADMIN
  - Target: form_id
  - Details: "Notified {notified_count} users"

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| INVALID_CHANNEL | 400 | channel not in {email, push, sms} |
| INVALID_TEMPLATE | 400 | template not in {expiry_reminder, reconsent_required} |
| FORM_NOT_FOUND | 404 | form_id does not exist |
| JOB_NOT_FOUND | 404 | job_id does not exist |

## Request Schema

### ExpiryReminderRequest

```json
{
  "form_id": "string (UUID, required)",
  "within_days": "integer (required, days until expiry to trigger reminder)",
  "channel": "email | push | sms (required)"
}
```

### TestNotificationRequest

```json
{
  "template": "expiry_reminder | reconsent_required (required)",
  "form_id": "string (UUID, required)",
  "version": "string (e.g. '2.0', required)",
  "user_id": "string (UUID, required)"
}
```

## Response Schema

### ExpiryReminderResponse

```json
{
  "notified": "integer (count of consents expiring within window)",
  "job_id": "string (UUID)"
}
```

### NotificationJobResponse

```json
{
  "job_id": "string (UUID)",
  "status": "running | completed | failed",
  "notified": "integer (actual notifications sent)",
  "failed": "integer (failed deliveries)",
  "completed_at": "string (ISO datetime) | null",
  "error_message": "string | null"
}
```

### TestNotificationResponse

```json
{
  "sent": "boolean (always true)",
  "preview_html": "string (HTML template preview)"
}
```

## Usage Examples

### Example 1: Send Expiry Reminders Weekly

**Workflow**:
1. Admin runs job every Monday morning
2. POST /notifications/expiry-reminder with within_days=30, channel=email
3. System finds all consents expiring in next 30 days
4. Returns job_id; async emails sent in background
5. Admin polls GET /notifications/jobs/{id} until completed
6. Checks notified count and error_message for issues

**Cron Job**:
```
0 8 * * 1 curl -X POST http://v1/notifications/expiry-reminder \
  -H "Authorization: Bearer $SYSTEM_TOKEN" \
  -d '{"form_id": "...", "within_days": 30, "channel": "email"}'
```

### Example 2: Test Before Deployment

**Workflow**:
1. QA wants to verify expiry_reminder template HTML
2. POST /notifications/test with template=expiry_reminder, form_id, version
3. System returns preview HTML without sending actual notifications
4. QA renders HTML in browser; verifies layout/branding
5. If satisfied, deploys to production

### Example 3: Monitor Job Status

**Workflow**:
1. POST /expiry-reminder returns job_id=abc123
2. Client stores job_id and polls every 5 seconds
3. GET /jobs/abc123 returns status=running
4. After 2 minutes, GET /jobs/abc123 returns status=completed, notified=47
5. Client displays success message to user

## Notes

- Notifications are sent asynchronously; expect 30 sec–5 min latency depending on system load
- Email/SMS channels not yet integrated (placeholder); admin must implement delivery adapter
- Test endpoint generates HTML but does not persist or send; safe for repeated testing
- Job status persisted in AsyncJob table; can be queried/reported separately
- Future: support template customization via database; support batch notification scheduling
- Expiry reminder within_days should be configured per organisation (e.g., 30 days = "expiry warning deadline")
