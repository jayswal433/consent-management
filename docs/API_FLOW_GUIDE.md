# EveryCRED DPDP Consent Management API Usage Flow Guide

Complete reference guide for integrating with the EveryCRED Digital Personal Data Protection (DPDP) Act 2023 Consent Management microservice. This document covers authentication, organisation setup, form lifecycle, consent grants, data subject rights, auditing, and analytics workflows.

**Base URL:** `http://localhost:8008/v1`

**API Version:** v1

**Last Updated:** 2026-05-22

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication Flow](#authentication-flow)
3. [Organisation Setup Flow](#organisation-setup-flow)
4. [Consent Form Lifecycle](#consent-form-lifecycle)
5. [Consent Grant Flow](#consent-grant-flow)
6. [Re-consent Flow](#re-consent-flow)
7. [DPDP Data Subject Rights Flow](#dpdp-data-subject-rights-flow)
8. [Audit & Compliance Flow](#audit--compliance-flow)
9. [Analytics Flow](#analytics-flow)
10. [Notification Flow](#notification-flow)
11. [RBAC & Permissions Reference](#rbac--permissions-reference)
12. [Error Handling](#error-handling)
13. [Common Scenarios](#common-scenarios)

---

## Quick Start

### 1. Register a New User (Citizen)

```bash
curl -X POST http://localhost:8008/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "citizen@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe",
    "phone": "+91-9876543210"
  }'
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "User created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "citizen@example.com",
    "full_name": "John Doe",
    "role": "citizen",
    "created_at": "2026-05-22T10:00:00+00:00"
  }
}
```

### 2. Login & Get Access Token

```bash
curl -X POST http://localhost:8008/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "username": "citizen@example.com",
    "password": "SecurePassword123!"
  }'
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Token issued successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900,
    "token_type": "Bearer",
    "scope": "read write"
  }
}
```

**Token Details:**
- Access token TTL: 900 seconds (15 minutes)
- Refresh token TTL: 604,800 seconds (7 days)
- JWT Algorithm: HS256
- JWT Payload: `{sub, role, org_id, type, exp, iat}`

### 3. Use Token in Subsequent Requests

```bash
# All protected endpoints require this header:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Authentication Flow

Complete authentication workflow for citizen registration, login, token refresh, and revocation.

### Step 1: Register Citizen

**Endpoint:** `POST /users`

**Authentication:** None (public endpoint)

**Request:**
```http
POST /v1/users
Content-Type: application/json

{
  "email": "jane.smith@example.com",
  "password": "SecurePass@123",
  "full_name": "Jane Smith",
  "phone": "+91-9876543211",
  "date_of_birth": "1990-05-15"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "User created successfully",
  "data": {
    "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "email": "jane.smith@example.com",
    "full_name": "Jane Smith",
    "phone": "+91-9876543211",
    "role": "citizen",
    "created_at": "2026-05-22T10:15:30+00:00"
  }
}
```

### Step 2: Login (Issue Token)

**Endpoint:** `POST /auth/token`

**Authentication:** None

**Request:**
```http
POST /v1/auth/token
Content-Type: application/json

{
  "grant_type": "password",
  "username": "jane.smith@example.com",
  "password": "SecurePass@123"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Token issued successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YmE3YjgxMC05ZGFkLTExZDEtODBiNC0wMGMwNGZkNDMwYzgiLCJyb2xlIjoiY2l0aXplbiIsIm9yZ19pZCI6bnVsbCwiZXhwIjoxNjI2OTkzMzMwLCJpYXQiOjE2MjY5OTI0MzB9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YmE3YjgxMC05ZGFkLTExZDEtODBiNC0wMGMwNGZkNDMwYzgiLCJleHAiOjE2MjcxNDIwMzB9...",
    "expires_in": 900,
    "token_type": "Bearer",
    "scope": "read write"
  }
}
```

### Step 3: Refresh Token (Before Expiry)

**Endpoint:** `POST /auth/refresh`

**Authentication:** Required (Bearer token)

**Request:**
```http
POST /v1/auth/refresh
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2YmE3YjgxMC05ZGFkLTExZDEtODBiNC0wMGMwNGZkNDMwYzgiLCJleHAiOjE2MjcxNDIwMzB9..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Token refreshed successfully",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 900,
    "token_type": "Bearer",
    "scope": "read write"
  }
}
```

### Step 4: Logout (Revoke Token)

**Endpoint:** `POST /auth/revoke`

**Authentication:** Required (Bearer token)

**Request:**
```http
POST /v1/auth/revoke
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type_hint": "access_token"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Token revoked successfully",
  "data": {
    "revoked": true,
    "revoked_at": "2026-05-22T10:30:00+00:00"
  }
}
```

---

## Organisation Setup Flow

Complete workflow for Super Admins to create and manage organisations.

### Step 1: Create Organisation

**Endpoint:** `POST /orgs`

**Permission:** `create_delete_org` (Super Admin only)

**Request:**
```http
POST /v1/orgs
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "TechCorp India Ltd.",
  "code": "TECHCORP",
  "country": "IN",
  "state": "KA",
  "dpo_email": "dpo@techcorp.com",
  "dpo_name": "Alice Johnson",
  "dpo_phone": "+91-9876543212",
  "industry": "Technology",
  "website": "https://techcorp.example.com"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Organisation created successfully",
  "data": {
    "id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "name": "TechCorp India Ltd.",
    "code": "TECHCORP",
    "country": "IN",
    "dpo_email": "dpo@techcorp.com",
    "dpo_name": "Alice Johnson",
    "created_at": "2026-05-22T11:00:00+00:00",
    "updated_at": "2026-05-22T11:00:00+00:00"
  }
}
```

### Step 2: View Organisation Details

**Endpoint:** `GET /orgs/{org_id}`

**Permission:** `view_org_profile`

**Request:**
```http
GET /v1/orgs/7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Organisation retrieved successfully",
  "data": {
    "id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "name": "TechCorp India Ltd.",
    "code": "TECHCORP",
    "country": "IN",
    "state": "KA",
    "dpo_email": "dpo@techcorp.com",
    "dpo_name": "Alice Johnson",
    "dpo_phone": "+91-9876543212",
    "industry": "Technology",
    "website": "https://techcorp.example.com",
    "created_at": "2026-05-22T11:00:00+00:00",
    "updated_at": "2026-05-22T11:00:00+00:00"
  }
}
```

### Step 3: Update DPO Details

**Endpoint:** `PATCH /orgs/{org_id}`

**Permission:** `update_org_settings`

**Request:**
```http
PATCH /v1/orgs/7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "dpo_email": "new_dpo@techcorp.com",
  "dpo_name": "Bob Wilson",
  "dpo_phone": "+91-9876543213"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Organisation updated successfully",
  "data": {
    "id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "name": "TechCorp India Ltd.",
    "dpo_email": "new_dpo@techcorp.com",
    "dpo_name": "Bob Wilson",
    "dpo_phone": "+91-9876543213",
    "updated_at": "2026-05-22T11:15:00+00:00"
  }
}
```

### Step 4: List All Organisations

**Endpoint:** `GET /orgs`

**Permission:** `create_delete_org` (Super Admin only)

**Request:**
```http
GET /v1/orgs?page=1&limit=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Organisations retrieved successfully",
  "data": {
    "items": [
      {
        "id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
        "name": "TechCorp India Ltd.",
        "code": "TECHCORP",
        "dpo_name": "Bob Wilson",
        "created_at": "2026-05-22T11:00:00+00:00"
      },
      {
        "id": "8a4d1b91-6c9g-5e3d-0f2b-4b9c8d0e2f3g",
        "name": "FinanceHub Solutions",
        "code": "FINHUB",
        "dpo_name": "Carol Davis",
        "created_at": "2026-05-22T11:30:00+00:00"
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 20
  }
}
```

---

## Consent Form Lifecycle

Complete workflow for creating, versioning, reviewing, publishing, and managing consent forms.

### Overview Diagram

```
DRAFT → CREATE VERSION → SUBMIT FOR REVIEW → PUBLISH → ACTIVE
                             ↓                              ↓
                        DPO_REVIEW                    CITIZEN_GRANT
                             ↓
                          PUBLISH
                             ↓
                          ACTIVE → ROLLBACK (to previous version)
                             ↓
                        DEACTIVATE
```

### Step 1: Create Form Draft

**Endpoint:** `POST /forms`

**Permission:** `create_consent_form`

**Request:**
```http
POST /v1/forms
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Customer Data Collection Form",
  "code": "CUSTOMER_DATA_V1",
  "org_id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
  "owner": "form-editor@techcorp.com",
  "purpose_short": "To collect and process customer information for account management and support services.",
  "purpose": "We collect your personal information to create and maintain your account, provide customer support, send service updates, and improve our service offerings. This is in accordance with your consent under the Digital Personal Data Protection Act, 2023.",
  "description": "A comprehensive form for collecting customer personal data",
  "legal_basis": "consent",
  "retention_days": 365,
  "expiry_days": 365,
  "third_parties": ["Stripe (payment processing)", "SendGrid (email delivery)"],
  "user_rights": ["access", "correction", "erasure", "data_portability"],
  "data_fields": [
    {
      "name": "email",
      "type": "email",
      "required": true,
      "optional": false
    },
    {
      "name": "phone",
      "type": "text",
      "required": false,
      "optional": true
    },
    {
      "name": "marketing_emails",
      "type": "checkbox",
      "required": false,
      "optional": true
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Form created successfully",
  "data": {
    "id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "name": "Customer Data Collection Form",
    "code": "CUSTOMER_DATA_V1",
    "status": "draft",
    "owner": "form-editor@techcorp.com",
    "created_at": "2026-05-22T12:00:00+00:00",
    "updated_at": "2026-05-22T12:00:00+00:00"
  }
}
```

### Step 2: Create Form Version

**Endpoint:** `POST /forms/{form_id}/versions`

**Permission:** `create_consent_form`

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "version_number": "v1.0",
  "changelog": "Initial version of customer data collection form",
  "data_fields": [
    {
      "name": "email",
      "type": "email",
      "required": true,
      "optional": false
    },
    {
      "name": "phone",
      "type": "text",
      "required": false,
      "optional": true
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Version created successfully",
  "data": {
    "id": "a0d4f9a3-8e1b-5f4c-2g5d-6b1e7c2f3g4a",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.0",
    "status": "draft",
    "created_at": "2026-05-22T12:10:00+00:00"
  }
}
```

### Step 3: Update Form Draft

**Endpoint:** `PATCH /forms/{form_id}`

**Permission:** `edit_form_draft`

**Request:**
```http
PATCH /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "owner": "new-owner@techcorp.com",
  "purpose_short": "Updated purpose for collecting customer data"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Form updated successfully",
  "data": {
    "id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "name": "Customer Data Collection Form",
    "owner": "new-owner@techcorp.com",
    "status": "draft",
    "updated_at": "2026-05-22T12:20:00+00:00"
  }
}
```

### Step 4: Submit Version for Review

**Endpoint:** `POST /forms/{form_id}/versions/{version}/submit`

**Permission:** `submit_for_review`

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions/v1.0/submit
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "reviewer_notes": "Form ready for DPO review. All mandatory fields are validated."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Version submitted for review successfully",
  "data": {
    "id": "a0d4f9a3-8e1b-5f4c-2g5d-6b1e7c2f3g4a",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.0",
    "status": "pending_review",
    "submitted_at": "2026-05-22T12:30:00+00:00"
  }
}
```

### Step 5: DPO Reviews & Publishes Version

**Endpoint:** `POST /forms/{form_id}/versions/{version}/publish`

**Permission:** `approve_publish_version` (DPO/Admin only)

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions/v1.0/publish
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "approved": true,
  "dpo_comments": "Form complies with DPDP Act 2023 requirements. Approved for publication.",
  "published_at": "2026-05-22T13:00:00+00:00"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Version published successfully",
  "data": {
    "id": "a0d4f9a3-8e1b-5f4c-2g5d-6b1e7c2f3g4a",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.0",
    "status": "published",
    "published_at": "2026-05-22T13:00:00+00:00",
    "published_by": "dpo@techcorp.com"
  }
}
```

### Step 6: Get Form Details

**Endpoint:** `GET /forms/{form_id}`

**Permission:** `view_form_details`

**Request:**
```http
GET /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Form retrieved successfully",
  "data": {
    "id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "name": "Customer Data Collection Form",
    "code": "CUSTOMER_DATA_V1",
    "status": "active",
    "owner": "form-editor@techcorp.com",
    "purpose": "We collect your personal information...",
    "retention_days": 365,
    "expiry_days": 365,
    "published_version": "v1.0",
    "created_at": "2026-05-22T12:00:00+00:00",
    "updated_at": "2026-05-22T13:00:00+00:00"
  }
}
```

### Step 7: List Form Versions

**Endpoint:** `GET /forms/{form_id}/versions`

**Permission:** `view_form_details`

**Request:**
```http
GET /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Versions retrieved successfully",
  "data": {
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "versions": [
      {
        "version": "v1.0",
        "status": "published",
        "published_at": "2026-05-22T13:00:00+00:00",
        "published_by": "dpo@techcorp.com",
        "consent_count": 1250
      }
    ]
  }
}
```

### Step 8: Compare Form Versions

**Endpoint:** `GET /forms/{form_id}/versions/diff?from_version={from}&to_version={to}`

**Permission:** `view_form_details`

**Request:**
```http
GET /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions/diff?from_version=v1.0&to_version=v1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Version diff retrieved successfully",
  "data": {
    "from_version": "v1.0",
    "to_version": "v1.1",
    "changes": {
      "purpose": {
        "old": "Previous purpose text...",
        "new": "Updated purpose text..."
      },
      "data_fields": {
        "added": [
          {
            "name": "address",
            "type": "text",
            "required": false
          }
        ],
        "removed": []
      }
    }
  }
}
```

### Step 9: Rollback to Previous Version

**Endpoint:** `POST /forms/{form_id}/versions/{version}/rollback`

**Permission:** `rollback_version`

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/versions/v1.1/rollback
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "rollback_reason": "v1.1 contains validation issues. Rolling back to v1.0"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Version rolled back successfully",
  "data": {
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "rolled_back_version": "v1.1",
    "active_version": "v1.0",
    "rolled_back_at": "2026-05-22T14:00:00+00:00"
  }
}
```

### Step 10: Deactivate Form

**Endpoint:** `POST /forms/{form_id}/deactivate`

**Permission:** `activate_deactivate_form`

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/deactivate
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "reason": "Form is no longer required for data collection",
  "revoke_existing_consents": false
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Form deactivated successfully",
  "data": {
    "id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "status": "inactive",
    "deactivated_at": "2026-05-22T14:15:00+00:00"
  }
}
```

### Step 11: Activate Form

**Endpoint:** `POST /forms/{form_id}/activate`

**Permission:** `activate_deactivate_form`

**Request:**
```http
POST /v1/forms/9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a/activate
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Form activated successfully",
  "data": {
    "id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "status": "active",
    "activated_at": "2026-05-22T14:30:00+00:00"
  }
}
```

---

## Consent Grant Flow

Complete workflow for citizens to check, grant, withdraw, and manage their consents.

### Step 1: Check Current Consent Status

**Endpoint:** `POST /consents/check`

**Permission:** `check_consent_service` (Public/Citizens)

**Request:**
```http
POST /v1/consents/check
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Consent check completed",
  "data": {
    "has_consent": true,
    "version": "v1.0",
    "reconsent_required": false,
    "status": "granted",
    "granted_at": "2026-05-01T10:00:00+00:00",
    "expires_at": "2027-05-01T10:00:00+00:00"
  }
}
```

### Step 2: Grant Consent

**Endpoint:** `POST /consents`

**Permission:** `grant_consent`

**Request:**
```http
POST /v1/consents
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "version": "v1.0",
  "optional_fields": ["phone", "marketing_emails"],
  "channel": "web",
  "ip_address": "203.0.113.1",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Consent granted successfully",
  "data": {
    "id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.0",
    "status": "granted",
    "granted_at": "2026-05-22T15:00:00+00:00",
    "expires_at": "2027-05-22T15:00:00+00:00",
    "optional_fields": ["phone", "marketing_emails"],
    "receipt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Step 3: Download Consent Receipt

**Endpoint:** `GET /consents/{consent_id}/receipt?format=json`

**Permission:** `download_consent_receipt`

**Request:**
```http
GET /v1/consents/b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e/receipt?format=json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Receipt retrieved successfully",
  "data": {
    "consent_id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "form_name": "Customer Data Collection Form",
    "form_code": "CUSTOMER_DATA_V1",
    "version": "v1.0",
    "granted_at": "2026-05-22T15:00:00+00:00",
    "expires_at": "2027-05-22T15:00:00+00:00",
    "purpose": "We collect your personal information to create and maintain your account...",
    "retention_period": "1 year",
    "data_fields": [
      {
        "name": "email",
        "required": true
      },
      {
        "name": "phone",
        "required": false,
        "selected": true
      }
    ],
    "third_parties": ["Stripe (payment processing)", "SendGrid (email delivery)"],
    "user_rights": ["access", "correction", "erasure", "data_portability"],
    "receipt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### Step 4: View Own Consents

**Endpoint:** `GET /users/{user_id}/consents`

**Permission:** `view_own_consents` or admin

**Request:**
```http
GET /v1/users/6ba7b810-9dad-11d1-80b4-00c04fd430c8/consents?status=granted
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Consents retrieved successfully",
  "data": {
    "items": [
      {
        "id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
        "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
        "form_name": "Customer Data Collection Form",
        "version": "v1.0",
        "status": "granted",
        "granted_at": "2026-05-22T15:00:00+00:00",
        "expires_at": "2027-05-22T15:00:00+00:00"
      }
    ],
    "total": 1,
    "page": 1
  }
}
```

### Step 5: Withdraw Consent

**Endpoint:** `POST /consents/{consent_id}/withdraw`

**Permission:** `withdraw_consent`

**Request:**
```http
POST /v1/consents/b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e/withdraw
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "reason": "User no longer wants to share marketing preferences",
  "channel": "web"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Consent withdrawn successfully",
  "data": {
    "consent_id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
    "status": "withdrawn",
    "withdrawn_at": "2026-05-22T16:00:00+00:00",
    "withdrawal_receipt_id": "c2f6b7d4-2g3b-5d4c-9e8f-0a1b2c3d4e5f"
  }
}
```

### Step 6: Decline Consent (Without Creating Record)

**Endpoint:** `POST /consents/{consent_id}/decline`

**Permission:** `grant_consent`

**Request:**
```http
POST /v1/consents/b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e/decline
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "version": "v1.0",
  "channel": "web"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Decline logged successfully",
  "data": {
    "logged": true,
    "audit_id": "d3g7c8e5-3h4c-6e5d-0f9g-1b2c3d4e5f6a"
  }
}
```

### Step 7: List All Consents (Admin/DPO)

**Endpoint:** `GET /consents`

**Permission:** `view_all_consents`

**Request:**
```http
GET /v1/consents?form_id=9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a&status=granted&page=1&limit=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Consents retrieved successfully",
  "data": {
    "items": [
      {
        "id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
        "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
        "version": "v1.0",
        "status": "granted",
        "granted_at": "2026-05-22T15:00:00+00:00",
        "expires_at": "2027-05-22T15:00:00+00:00"
      }
    ],
    "total": 1250,
    "page": 1,
    "limit": 20
  }
}
```

---

## Re-consent Flow

Workflow for handling re-consent requirements when a form version is updated.

### Overview

When a form version is published with significant changes, users with existing consent to the previous version must re-consent. This flow identifies affected users and facilitates the re-consent process.

### Step 1: Check Pending Reconsent

**Endpoint:** `GET /reconsent/pending?form_id={form_id}`

**Permission:** `view_all_consents`

**Request:**
```http
GET /v1/reconsent/pending?form_id=9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a&page=1&limit=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Pending reconsent users retrieved",
  "data": {
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "current_version": "v1.1",
    "users_requiring_reconsent": [
      {
        "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "current_consent_version": "v1.0",
        "granted_at": "2026-05-01T10:00:00+00:00"
      }
    ],
    "total": 1250,
    "page": 1,
    "limit": 20
  }
}
```

### Step 2: Notify Users for Reconsent

**Endpoint:** `POST /reconsent/notify`

**Permission:** `trigger_notifications`

**Request:**
```http
POST /v1/reconsent/notify
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "version": "v1.1",
  "user_ids": null,
  "notification_channels": ["email"],
  "expiry_days": 30
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Notification job created successfully",
  "data": {
    "job_id": "e4h8d9f6-4i5d-7f6e-1g0h-2c3d4e5f6g7a",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.1",
    "status": "queued",
    "users_notified": 1250,
    "created_at": "2026-05-22T17:00:00+00:00"
  }
}
```

### Step 3: Poll Job Status

**Endpoint:** `GET /reconsent/jobs/{job_id}`

**Permission:** `view_all_consents`

**Request:**
```http
GET /v1/reconsent/jobs/e4h8d9f6-4i5d-7f6e-1g0h-2c3d4e5f6g7a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Job status retrieved",
  "data": {
    "job_id": "e4h8d9f6-4i5d-7f6e-1g0h-2c3d4e5f6g7a",
    "status": "completed",
    "progress": {
      "total": 1250,
      "completed": 1250,
      "failed": 0
    },
    "started_at": "2026-05-22T17:00:00+00:00",
    "completed_at": "2026-05-22T17:05:00+00:00"
  }
}
```

### Step 4: Bulk Revoke Stale Consents (Dry Run)

**Endpoint:** `POST /reconsent/bulk-revoke`

**Permission:** `bulk_revoke`

**Request (First: Dry Run):**
```http
POST /v1/reconsent/bulk-revoke
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "older_than": "v1.0",
  "dry_run": true
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Bulk revoke operation completed",
  "data": {
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "dry_run": true,
    "consents_to_revoke": 1250,
    "estimated_impact": {
      "users_affected": 1250,
      "consent_records": 1250
    },
    "operation_id": "f5i9e0g7-5j6e-8g7f-2h1i-3d4e5f6g7h8a"
  }
}
```

### Step 5: Execute Bulk Revocation

**Endpoint:** `POST /reconsent/bulk-revoke`

**Permission:** `bulk_revoke`

**Request (Execute: dry_run=false):**
```http
POST /v1/reconsent/bulk-revoke
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "older_than": "v1.0",
  "dry_run": false
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Bulk revoke operation completed",
  "data": {
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "dry_run": false,
    "consents_revoked": 1250,
    "revocation_summary": {
      "successful": 1250,
      "failed": 0
    },
    "revoked_at": "2026-05-22T17:30:00+00:00",
    "operation_id": "f5i9e0g7-5j6e-8g7f-2h1i-3d4e5f6g7h8a"
  }
}
```

---

## DPDP Data Subject Rights Flow

Complete workflow for citizens to exercise data subject rights under DPDP Act 2023.

### Step 1: View Available Rights

**Endpoint:** `GET /users/{user_id}/rights`

**Permission:** Own user or admin

**Request:**
```http
GET /v1/users/6ba7b810-9dad-11d1-80b4-00c04fd430c8/rights
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Rights retrieved successfully",
  "data": {
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "available_rights": [
      {
        "right": "access",
        "description": "Right to access personal data",
        "available": true
      },
      {
        "right": "correction",
        "description": "Right to correct inaccurate data",
        "available": true
      },
      {
        "right": "erasure",
        "description": "Right to erasure (right to be forgotten)",
        "available": true
      },
      {
        "right": "data_portability",
        "description": "Right to data portability",
        "available": true
      }
    ]
  }
}
```

### Step 2: Request Data Access (Included in View Own Consents)

**Endpoint:** `GET /users/{user_id}/consents`

*See Consent Grant Flow - Step 4*

### Step 3: Request Data Portability

**Endpoint:** `POST /users/{user_id}/rights/portability`

**Permission:** `export_user_data`

**Request:**
```http
POST /v1/users/6ba7b810-9dad-11d1-80b4-00c04fd430c8/rights/portability
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "format": "json",
  "include_audit_trail": true,
  "include_consent_receipts": true
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Data portability request created",
  "data": {
    "request_id": "g6j0f1h8-6k7f-9h8g-3i2j-4e5f6g7h8i9a",
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "format": "json",
    "status": "processing",
    "created_at": "2026-05-22T18:00:00+00:00",
    "estimated_completion": "2026-05-23T18:00:00+00:00"
  }
}
```

### Step 4: Register Nominee

**Endpoint:** `POST /users/{user_id}/nominee`

**Permission:** `register_nominee`

**Request:**
```http
POST /v1/users/6ba7b810-9dad-11d1-80b4-00c04fd430c8/nominee
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "nominee_name": "Alice Smith",
  "nominee_email": "nominee@example.com",
  "relationship": "spouse",
  "legal_document_url": "https://storage.example.com/power_of_attorney.pdf"
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Nominee registered successfully",
  "data": {
    "nominee_id": "h7k1g2i9-7l8g-0i9h-4j3k-5f6g7h8i9j0a",
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "nominee_name": "Alice Smith",
    "nominee_email": "nominee@example.com",
    "status": "pending_verification",
    "created_at": "2026-05-22T18:30:00+00:00"
  }
}
```

### Step 5: Request Right to Erasure

**Endpoint:** `POST /users/{user_id}/rights/erasure`

**Permission:** `erasure_request`

**Request:**
```http
POST /v1/users/6ba7b810-9dad-11d1-80b4-00c04fd430c8/rights/erasure
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "reason": "User requested permanent account deletion",
  "include_consents": true,
  "include_audit_trail": false
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Erasure request submitted",
  "data": {
    "request_id": "i8l2h3j0-8m9h-1j0i-5k4l-6g7h8i9j0k1a",
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "status": "scheduled",
    "erasure_will_occur_at": "2026-05-29T18:30:00+00:00",
    "grace_period_days": 7
  }
}
```

---

## Audit & Compliance Flow

Complete workflow for DPOs and admins to query, verify, and export audit logs for compliance.

### Step 1: Query Audit Log

**Endpoint:** `GET /audit`

**Permission:** `view_audit_log`

**Request:**
```http
GET /v1/audit?action=consent_granted&form_id=9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a&from_date=2026-05-01T00:00:00Z&to_date=2026-05-22T23:59:59Z&page=1&limit=50
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Audit logs retrieved successfully",
  "data": {
    "items": [
      {
        "id": "j9m3i4k1-9n0i-2k1j-6l5m-7h8i9j0k1l2a",
        "actor_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "actor_type": "citizen",
        "action": "consent_granted",
        "resource_type": "consent",
        "resource_id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
        "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
        "details": {
          "version": "v1.0",
          "optional_fields": ["phone", "marketing_emails"],
          "ip_address": "203.0.113.1"
        },
        "timestamp": "2026-05-22T15:00:00+00:00",
        "hash": "sha256:abc123def456...",
        "previous_hash": "sha256:xyz789uvw012..."
      }
    ],
    "total": 1250,
    "page": 1,
    "limit": 50
  }
}
```

### Step 2: Verify Tamper Evidence (Hash Chain)

**Endpoint:** `GET /audit/{audit_id}`

**Permission:** `view_audit_log`

**Request:**
```http
GET /v1/audit/j9m3i4k1-9n0i-2k1j-6l5m-7h8i9j0k1l2a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Audit entry retrieved successfully",
  "data": {
    "id": "j9m3i4k1-9n0i-2k1j-6l5m-7h8i9j0k1l2a",
    "actor_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "actor_type": "citizen",
    "action": "consent_granted",
    "resource_type": "consent",
    "resource_id": "b1e5a6c3-1f2a-4c3b-8d7e-9f0a1b2c3d4e",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "details": {
      "version": "v1.0",
      "optional_fields": ["phone", "marketing_emails"],
      "ip_address": "203.0.113.1",
      "user_agent": "Mozilla/5.0..."
    },
    "timestamp": "2026-05-22T15:00:00+00:00",
    "hash": "sha256:abc123def456...",
    "previous_hash": "sha256:xyz789uvw012...",
    "hash_chain_verified": true,
    "tampering_detected": false
  }
}
```

### Step 3: Export Audit Log

**Endpoint:** `POST /audit/export`

**Permission:** `export_audit_log`

**Request:**
```http
POST /v1/audit/export
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "format": "csv",
  "from_date": "2026-05-01T00:00:00Z",
  "to_date": "2026-05-22T23:59:59Z",
  "filters": {
    "action": "consent_granted",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a"
  }
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Audit export started",
  "data": {
    "job_id": "k0n4j5l2-0o1j-3l2k-7m6n-8i9j0k1l2m3a",
    "format": "csv",
    "status": "queued",
    "total_records": 1250,
    "created_at": "2026-05-22T19:00:00+00:00",
    "estimated_completion": "2026-05-22T19:10:00+00:00"
  }
}
```

### Step 4: Poll Export Job Status

**Endpoint:** `GET /audit/export/{job_id}`

**Permission:** `export_audit_log`

**Request:**
```http
GET /v1/audit/export/k0n4j5l2-0o1j-3l2k-7m6n-8i9j0k1l2m3a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Job status retrieved",
  "data": {
    "job_id": "k0n4j5l2-0o1j-3l2k-7m6n-8i9j0k1l2m3a",
    "status": "completed",
    "format": "csv",
    "total_records": 1250,
    "download_url": "https://storage.example.com/exports/k0n4j5l2.csv",
    "download_url_expires_at": "2026-05-23T19:00:00+00:00",
    "file_size_bytes": 512000,
    "created_at": "2026-05-22T19:00:00+00:00",
    "completed_at": "2026-05-22T19:08:30+00:00"
  }
}
```

---

## Analytics Flow

Complete workflow for admins and analysts to query consent and form analytics.

### Step 1: Get Consent Trend

**Endpoint:** `GET /analytics/consent-trend?days=30`

**Permission:** `view_analytics`

**Request:**
```http
GET /v1/analytics/consent-trend?days=30&form_id=9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Consent trend retrieved successfully",
  "data": {
    "period": {
      "from": "2026-04-22T00:00:00+00:00",
      "to": "2026-05-22T23:59:59+00:00",
      "days": 30
    },
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "trend": [
      {
        "date": "2026-04-22",
        "granted": 50,
        "withdrawn": 2,
        "declined": 5,
        "net_change": 43
      },
      {
        "date": "2026-04-23",
        "granted": 55,
        "withdrawn": 1,
        "declined": 3,
        "net_change": 51
      }
    ],
    "summary": {
      "total_granted": 1250,
      "total_withdrawn": 45,
      "total_declined": 85,
      "net_active": 1120
    }
  }
}
```

### Step 2: Get KPI Summary

**Endpoint:** `GET /analytics/summary`

**Permission:** `view_analytics`

**Request:**
```http
GET /v1/analytics/summary?org_id=7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f&from_date=2026-05-01T00:00:00Z&to_date=2026-05-22T23:59:59Z
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Summary statistics retrieved successfully",
  "data": {
    "org_id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "period": {
      "from": "2026-05-01T00:00:00+00:00",
      "to": "2026-05-22T23:59:59+00:00"
    },
    "forms": {
      "total": 5,
      "active": 4,
      "inactive": 1,
      "total_versions": 8
    },
    "consents": {
      "total_granted": 3500,
      "total_withdrawn": 120,
      "total_declined": 250,
      "active": 3130,
      "average_grant_rate": 0.93
    },
    "users": {
      "total_registered": 4000,
      "users_with_consent": 3380,
      "consent_adoption_rate": 0.845
    }
  }
}
```

### Step 3: Get Form Status Breakdown

**Endpoint:** `GET /analytics/forms-by-status`

**Permission:** `view_analytics`

**Request:**
```http
GET /v1/analytics/forms-by-status?org_id=7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Forms by status retrieved successfully",
  "data": {
    "org_id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "status_breakdown": {
      "draft": 2,
      "pending_review": 1,
      "published": 4,
      "inactive": 1
    },
    "total_forms": 8
  }
}
```

### Step 4: Get Top Forms by Consent

**Endpoint:** `GET /analytics/top-forms?limit=5`

**Permission:** `view_analytics`

**Request:**
```http
GET /v1/analytics/top-forms?limit=5&org_id=7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Top forms retrieved successfully",
  "data": {
    "org_id": "7f3c0a80-5b8f-4d2c-9e1a-3a8b7c9d1e2f",
    "limit": 5,
    "forms": [
      {
        "rank": 1,
        "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
        "form_name": "Customer Data Collection Form",
        "consent_count": 1250,
        "grant_rate": 0.96,
        "withdrawal_rate": 0.03,
        "decline_rate": 0.01
      },
      {
        "rank": 2,
        "form_id": "a0d5g0d3-8e1b-5f4c-2g5d-6b1e7c2f3g4a",
        "form_name": "Marketing Preferences Form",
        "consent_count": 892,
        "grant_rate": 0.89,
        "withdrawal_rate": 0.08,
        "decline_rate": 0.03
      }
    ]
  }
}
```

---

## Notification Flow

Complete workflow for sending notifications to users.

### Step 1: Send Expiry Reminders

**Endpoint:** `POST /notifications/expiry-reminder`

**Permission:** `trigger_notifications`

**Request:**
```http
POST /v1/notifications/expiry-reminder
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "days_until_expiry": 30,
  "form_ids": ["9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a"],
  "channels": ["email"],
  "test_mode": false
}
```

**Response (201 Created):**
```json
{
  "status": "success",
  "message": "Expiry reminder job created successfully",
  "data": {
    "job_id": "l1o5k6m3-1p2k-4m3l-8n7o-9j0k1l2m3n4a",
    "status": "queued",
    "users_to_notify": 450,
    "created_at": "2026-05-22T19:30:00+00:00"
  }
}
```

### Step 2: Poll Notification Job Status

**Endpoint:** `GET /notifications/jobs/{job_id}`

**Permission:** `view_all_consents`

**Request:**
```http
GET /v1/notifications/jobs/l1o5k6m3-1p2k-4m3l-8n7o-9j0k1l2m3n4a
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Job status retrieved",
  "data": {
    "job_id": "l1o5k6m3-1p2k-4m3l-8n7o-9j0k1l2m3n4a",
    "status": "completed",
    "progress": {
      "total": 450,
      "sent": 445,
      "failed": 5
    },
    "started_at": "2026-05-22T19:30:00+00:00",
    "completed_at": "2026-05-22T19:35:00+00:00"
  }
}
```

### Step 3: Send Test Notification

**Endpoint:** `POST /notifications/test`

**Permission:** `approve_publish_version`

**Request:**
```http
POST /v1/notifications/test
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "notification_type": "reconsent_required",
  "recipient_email": "test@example.com"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Test notification sent",
  "data": {
    "notification_id": "m2p6l7n4-2q3l-5n4m-9o8p-0k1l2m3n4o5a",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "notification_type": "reconsent_required",
    "recipient": "test@example.com",
    "preview_html": "<html>...",
    "sent_at": "2026-05-22T20:00:00+00:00"
  }
}
```

---

## RBAC & Permissions Reference

Complete Role-Based Access Control (RBAC) matrix for all user roles in the DPDP Consent Management system.

### User Roles

| Role | Description | Use Case |
|------|-------------|----------|
| `super_admin` | System-wide administrator | System administration, organisation creation, compliance oversight |
| `org_admin` | Organisation-level administrator | Organisation management, team oversight, form publishing approval |
| `form_editor` | Form creation and editing | Creating and drafting consent forms |
| `dpo_reviewer` | Data Protection Officer | Reviewing and approving forms, compliance verification |
| `read_only_analyst` | Analyst with read-only access | Analytics and reporting, audit log review |
| `citizen` | End user / data subject | Granting/withdrawing consents, accessing own data |
| `system_service` | Internal service account | Automated consent checks, notifications, system operations |

### Permission Matrix

| Permission | Description | Super Admin | Org Admin | Form Editor | DPO Reviewer | Analyst | Citizen | System Service |
|------------|-------------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| **Organisation** |
| `create_delete_org` | Create/delete organisations | ✓ | | | | | |  |
| `view_org_profile` | View org details | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| `update_org_settings` | Update DPO details, settings | ✓ | ✓ | | | | | |
| `manage_team_members` | Add/remove team members | ✓ | ✓ | | | | | |
| **Forms** |
| `create_consent_form` | Create new forms | ✓ | ✓ | ✓ | | | | |
| `edit_form_draft` | Edit draft versions | ✓ | ✓ | ✓ | | | | |
| `submit_for_review` | Submit form for review | ✓ | ✓ | ✓ | | | | |
| `approve_publish_version` | Publish form version | ✓ | ✓ | | ✓ | | | |
| `rollback_version` | Rollback to previous version | ✓ | ✓ | | | | | |
| `activate_deactivate_form` | Activate/deactivate forms | ✓ | ✓ | | | | | |
| `view_form_details` | View form details | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ |
| **Consents** |
| `grant_consent` | Grant consent | ✓ | ✓ | | | | ✓ | ✓ |
| `withdraw_consent` | Withdraw consent | ✓ | ✓ | | | | ✓ | |
| `view_own_consents` | View own consents | ✓ | ✓ | | | | ✓ | |
| `download_consent_receipt` | Download consent receipt | ✓ | ✓ | | | | ✓ | |
| `view_all_consents` | View all consents | ✓ | ✓ | | ✓ | ✓ | | ✓ |
| `check_consent_service` | Check consent status | ✓ | ✓ | | | | | ✓ |
| `bulk_revoke` | Bulk revoke consents | ✓ | ✓ | | | | | ✓ |
| **Audit & Compliance** |
| `view_audit_log` | View audit logs | ✓ | ✓ | | ✓ | ✓ | | |
| `export_audit_log` | Export audit logs | ✓ | ✓ | | ✓ | | | |
| **Data Subject Rights** |
| `export_user_data` | Data portability request | ✓ | ✓ | | | | ✓ | |
| `register_nominee` | Register nominee | ✓ | ✓ | | | | ✓ | |
| `erasure_request` | Right to erasure | ✓ | ✓ | | | | ✓ | |
| **Notifications & Analytics** |
| `trigger_notifications` | Send notifications | ✓ | ✓ | | | | | ✓ |
| `view_analytics` | View analytics | ✓ | ✓ | | ✓ | ✓ | | |
| **Authentication** |
| `issue_jwt` | Issue JWT tokens | ✓ | | | | | ✓ | ✓ |
| `revoke_token` | Revoke JWT tokens | ✓ | ✓ | | | | ✓ | |
| `introspect_token` | Introspect tokens | ✓ | | | | | | ✓ |
| `manage_rbac_roles` | Manage roles/permissions | ✓ | | | | | | |

---

## Error Handling

All error responses follow a standard error format.

### Error Response Format

```json
{
  "status": "fail",
  "message": "Human-readable error message",
  "data": {
    "error": "ERROR_CODE"
  }
}
```

### Common Error Codes & HTTP Status Codes

| HTTP Status | Error Code | Description | Example Scenario |
|------------|-----------|-------------|------------------|
| 400 | `BAD_REQUEST` | Invalid request parameters | Missing required field, invalid format |
| 401 | `TOKEN_EXPIRED` | JWT token has expired | Access token TTL exceeded (15 minutes) |
| 401 | `MISSING_CREDENTIALS` | No bearer token provided | Authorization header missing |
| 401 | `INVALID_SIGNATURE` | Token signature invalid | Token tampered with |
| 401 | `DECODE_ERROR` | Failed to decode token | Malformed JWT |
| 403 | `INSUFFICIENT_SCOPE` | User lacks required permission | Citizen trying to publish form |
| 403 | `ACCESS_DENIED` | Access denied | User trying to access another user's consents |
| 403 | `NO_ROLE` | No role found in token | JWT missing role claim |
| 403 | `INVALID_ROLE` | Unknown role value | Unexpected role in JWT |
| 404 | `RESOURCE_NOT_FOUND` | Resource does not exist | Form ID not found |
| 409 | `CONSENT_ALREADY_GRANTED` | Consent already exists | User granted consent twice for same version |
| 409 | `DUPLICATE_RESOURCE` | Resource already exists | Form code already taken |
| 422 | `PUBLISH_NOT_IN_REVIEW` | Cannot publish non-review version | Form version not pending review |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests | Rate limiting in effect |
| 500 | `INTERNAL_ERROR` | Server error | Unexpected exception |

### Example Error Response

**Request:**
```http
POST /v1/consents
Authorization: Bearer invalid_token
Content-Type: application/json

{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
  "version": "v1.0"
}
```

**Response (401 Unauthorized):**
```json
{
  "status": "fail",
  "message": "Token has expired",
  "data": {
    "error": "TOKEN_EXPIRED"
  }
}
```

---

## Common Scenarios

### Scenario 1: New User Complete Onboarding

**Goal:** Register a new user and grant initial consent to a form.

**Flow:**

```bash
# Step 1: Register user
curl -X POST http://localhost:8008/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecurePass@123",
    "full_name": "New User"
  }'

# Save user_id from response (e.g., 6ba7b810-...)

# Step 2: Login
curl -X POST http://localhost:8008/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "username": "newuser@example.com",
    "password": "SecurePass@123"
  }'

# Save access_token from response

# Step 3: Check existing consent
curl -X POST http://localhost:8008/v1/consents/check \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a"
  }'

# Step 4: If no consent, grant it
curl -X POST http://localhost:8008/v1/consents \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "form_id": "9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a",
    "version": "v1.0",
    "optional_fields": ["phone"],
    "channel": "web",
    "ip_address": "203.0.113.1"
  }'

# Step 5: Get consent receipt
curl -X GET http://localhost:8008/v1/consents/{consent_id}/receipt \
  -H "Authorization: Bearer {access_token}"
```

### Scenario 2: DPO Publishes New Form Version

**Goal:** Form editor creates a new version and DPO publishes it.

**Flow:**

```bash
# Step 1: Form Editor creates form draft (as form_editor user)
curl -X POST http://localhost:8008/v1/forms \
  -H "Authorization: Bearer {form_editor_token}" \
  -H "Content-Type: application/json" \
  -d '{...form data...}'

# Save form_id

# Step 2: Create version
curl -X POST http://localhost:8008/v1/forms/{form_id}/versions \
  -H "Authorization: Bearer {form_editor_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "version_number": "v1.0",
    "changelog": "Initial version"
  }'

# Step 3: Submit for review
curl -X POST http://localhost:8008/v1/forms/{form_id}/versions/v1.0/submit \
  -H "Authorization: Bearer {form_editor_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewer_notes": "Ready for DPO review"
  }'

# Step 4: DPO publishes (as dpo_reviewer user)
curl -X POST http://localhost:8008/v1/forms/{form_id}/versions/v1.0/publish \
  -H "Authorization: Bearer {dpo_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "dpo_comments": "Compliant with DPDP Act"
  }'

# Step 5: Trigger reconsent notifications if form had previous version
curl -X POST http://localhost:8008/v1/reconsent/notify \
  -H "Authorization: Bearer {dpo_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "form_id": "{form_id}",
    "version": "v1.0",
    "notification_channels": ["email"],
    "expiry_days": 30
  }'
```

### Scenario 3: Compliance Audit Report

**Goal:** DPO generates audit log export for compliance reporting.

**Flow:**

```bash
# Step 1: Query audit logs for period
curl -X GET "http://localhost:8008/v1/audit?from_date=2026-05-01T00:00:00Z&to_date=2026-05-22T23:59:59Z&limit=100" \
  -H "Authorization: Bearer {dpo_token}"

# Step 2: Start export job
curl -X POST http://localhost:8008/v1/audit/export \
  -H "Authorization: Bearer {dpo_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "csv",
    "from_date": "2026-05-01T00:00:00Z",
    "to_date": "2026-05-22T23:59:59Z",
    "filters": {
      "action": "consent_granted"
    }
  }'

# Save job_id

# Step 3: Poll job status
curl -X GET http://localhost:8008/v1/audit/export/{job_id} \
  -H "Authorization: Bearer {dpo_token}"

# Step 4: Download when completed
# Use download_url from response to fetch CSV file
```

### Scenario 4: Handle Consent Expiry

**Goal:** Send reminders to users before consent expires and manage expired consents.

**Flow:**

```bash
# Step 1: Check analytics for expiring consents
curl -X GET "http://localhost:8008/v1/analytics/consent-trend?days=30" \
  -H "Authorization: Bearer {admin_token}"

# Step 2: Send expiry reminders
curl -X POST http://localhost:8008/v1/notifications/expiry-reminder \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "days_until_expiry": 30,
    "form_ids": ["9c5e2c72-7d0a-4e3b-1f4c-5a0d6b1e2f3a"],
    "channels": ["email"]
  }'

# Step 3: Poll job
curl -X GET http://localhost:8008/v1/notifications/jobs/{job_id} \
  -H "Authorization: Bearer {admin_token}"

# Step 4: After expiry, monitor for withdrawn/lapsed consents
curl -X GET "http://localhost:8008/v1/consents?status=expired&page=1" \
  -H "Authorization: Bearer {admin_token}"
```

---

## Summary

This API Usage Flow Guide provides comprehensive coverage of the EveryCRED DPDP Consent Management system. Key takeaways:

1. **Authentication:** All protected endpoints require JWT Bearer tokens with 15-minute TTL and 7-day refresh token.
2. **RBAC:** Seven roles control access; permissions are granular and role-based.
3. **Form Lifecycle:** Forms progress from draft → version → review → publish → active, with rollback capability.
4. **Consent Workflow:** Citizens grant, withdraw, and manage consents; DPOs oversee compliance.
5. **Re-consent:** Handled automatically when form versions change; bulk operations support dry-run mode.
6. **Data Subject Rights:** Supports access, portability, erasure, and nominee registration per DPDP Act 2023.
7. **Audit & Compliance:** Immutable audit logs with hash chain verification for tamper detection.
8. **Analytics:** Real-time consent trends, KPIs, and form metrics for stakeholder reporting.
9. **Error Handling:** Standard error format with specific codes for debugging integration issues.

For further assistance, consult the individual feature documentation or contact your technical support team.

---

**Document Version:** 1.0

**Last Updated:** 2026-05-22

**API Version:** v1

**Revision:** Initial comprehensive guide
