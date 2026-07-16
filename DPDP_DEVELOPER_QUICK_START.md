# DPDP Quick Start Guide for Developers

This guide provides code snippets and examples for implementing features on top of the DPDP foundation layer.

## Common Import Patterns

```python
# Encryption utilities
from app.core.security.crypto import (
    encrypt_field, decrypt_field, sha256_hash,
    hmac_sha256_sign, hmac_sha256_verify, get_dek
)

# RBAC
from app.core.security.rbac import (
    UserRole, Permission, require_permission, get_jwt_claims, ROLE_PERMISSIONS
)

# Audit logging
from app.core.security.audit_writer import write_audit_entry

# Models
from app.models.orm import (
    Org, DpdpUser, ConsentForm, FormVersion, DpdpConsent,
    AuditLog, Nomination, AsyncJob,
    ConsentStatus, FormStatus, VersionStatus
)

# Database
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config.database import get_db_session
```

## Example 1: Protecting a Route with Permission Check

```python
from fastapi import APIRouter, Depends
from app.core.security.rbac import require_permission, Permission, get_jwt_claims

router = APIRouter(prefix="/v1/forms", tags=["forms"])

@router.post("/")
async def create_consent_form(
    form_data: FormCreateSchema,
    token_data: dict = Depends(require_permission(Permission.CREATE_CONSENT_FORM)),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a new consent form.
    Requires: CREATE_CONSENT_FORM permission
    """
    user_id = token_data["sub"]
    org_id = token_data["org_id"]
    role = token_data["role"]
    
    # Your business logic here
    form = ConsentForm(
        org_id=org_id,
        name=form_data.name,
        code=form_data.code,
        purpose=form_data.purpose,
        status=FormStatus.DRAFT.value
    )
    session.add(form)
    await session.flush()
    
    # Log the action
    await write_audit_entry(
        session=session,
        actor=user_id,
        actor_type="admin",
        action="form_created",
        target=form.id,
        details=f"Created form: {form.name}",
        org_id=org_id
    )
    await session.commit()
    return form
```

## Example 2: Encrypting/Decrypting Sensitive Data

```python
from app.core.security.crypto import encrypt_field, decrypt_field, sha256_hash, get_dek

async def create_user(
    user_data: UserCreateSchema,
    session: AsyncSession = Depends(get_db_session)
):
    """Create a user with encrypted PII."""
    dek = get_dek()
    
    # Encrypt sensitive fields
    encrypted_name = encrypt_field(user_data.name, dek)
    encrypted_email = encrypt_field(user_data.email, dek)
    encrypted_phone = encrypt_field(user_data.phone or "", dek)
    
    # Create hash fields for searchable lookups
    email_hash = sha256_hash(user_data.email)
    name_hash = sha256_hash(user_data.name)
    phone_hash = sha256_hash(user_data.phone or "") if user_data.phone else None
    
    user = DpdpUser(
        name=encrypted_name,
        name_hash=name_hash,
        email=encrypted_email,
        email_hash=email_hash,
        phone=encrypted_phone,
        phone_hash=phone_hash,
        role=user_data.role,
        password_hash=hash_password(user_data.password),
        is_active="1"
    )
    
    session.add(user)
    await session.commit()
    return user

async def get_user_by_email(email: str, session: AsyncSession):
    """Find user by email (search using hash)."""
    dek = get_dek()
    email_hash = sha256_hash(email)
    
    user = await session.scalar(
        select(DpdpUser).where(DpdpUser.email_hash == email_hash)
    )
    
    if user:
        # Decrypt email to verify (in case of hash collision, though unlikely)
        decrypted_email = decrypt_field(user.email, dek)
        if decrypted_email == email:
            return user
    
    return None
```

## Example 3: Recording Audit Events

```python
async def withdraw_consent(
    consent_id: str,
    token_data: dict = Depends(get_jwt_claims),
    session: AsyncSession = Depends(get_db_session)
):
    """Withdraw a user's consent and audit the action."""
    consent = await session.get(DpdpConsent, consent_id)
    
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    
    # Update consent
    consent.status = ConsentStatus.WITHDRAWN.value
    consent.withdrawn_at = datetime.now(UTC)
    
    # Record audit entry
    await write_audit_entry(
        session=session,
        actor=token_data["sub"],
        actor_type="user",
        action="consent_withdrawn",
        target=consent.form_id,
        version=consent.version,
        details=f"User withdrew consent for form {consent.form_id}",
        org_id=consent.user.org_id
    )
    
    await session.commit()
    return consent
```

## Example 4: Checking User Permissions Programmatically

```python
def can_user_perform_action(
    user_role: UserRole,
    required_permission: Permission
) -> bool:
    """Check if a role has permission without making HTTP request."""
    from app.core.security.rbac import ROLE_PERMISSIONS
    
    allowed_permissions = ROLE_PERMISSIONS.get(user_role, set())
    return required_permission in allowed_permissions

# Usage:
role = UserRole.FORM_EDITOR
if can_user_perform_action(role, Permission.APPROVE_PUBLISH_VERSION):
    # User can approve
    pass
else:
    # User cannot approve (DPO_REVIEWER can, but FORM_EDITOR cannot)
    pass
```

## Example 5: Creating a Form with Versions

```python
async def create_form_with_version(
    form_data: FormCreateSchema,
    token_data: dict = Depends(require_permission(Permission.CREATE_CONSENT_FORM)),
    session: AsyncSession = Depends(get_db_session)
):
    """Create a consent form with initial version."""
    user_id = token_data["sub"]
    org_id = token_data["org_id"]
    
    # Create form
    form = ConsentForm(
        org_id=org_id,
        name=form_data.name,
        code=form_data.code.upper(),
        purpose=form_data.purpose,
        legal_basis=form_data.legal_basis or LegalBasis.CONSENT.value,
        retention_days=str(form_data.retention_days or 365),
        expiry_days=str(form_data.expiry_days or 365),
        status=FormStatus.DRAFT.value
    )
    session.add(form)
    await session.flush()
    
    # Create initial version
    version = FormVersion(
        form_id=form.id,
        version="v1.0",
        status=VersionStatus.DRAFT.value,
        purpose=form_data.purpose,
        legal_basis=form_data.legal_basis or LegalBasis.CONSENT.value,
        retention_days=str(form_data.retention_days or 365),
        expiry_days=str(form_data.expiry_days or 365),
        title=form.name,
        data_fields=form_data.data_fields or {}
    )
    session.add(version)
    
    # Audit
    await write_audit_entry(
        session=session,
        actor=user_id,
        actor_type="admin",
        action="form_created",
        target=form.id,
        version="v1.0",
        details=f"Created form {form.name} with version v1.0",
        org_id=org_id
    )
    
    await session.commit()
    return form
```

## Example 6: Publishing a Form Version

```python
async def publish_version(
    form_id: str,
    version: str,
    token_data: dict = Depends(require_permission(Permission.APPROVE_PUBLISH_VERSION)),
    session: AsyncSession = Depends(get_db_session)
):
    """Publish a form version (DPO Reviewer only)."""
    user_id = token_data["sub"]
    
    # Get version
    form_version = await session.scalar(
        select(FormVersion)
        .where(FormVersion.form_id == form_id)
        .where(FormVersion.version == version)
    )
    
    if not form_version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Update version status
    form_version.status = VersionStatus.ACTIVE.value
    form_version.published_at = datetime.now(UTC)
    form_version.published_by = user_id
    
    # Update form's active version
    form = await session.get(ConsentForm, form_id)
    form.active_version = version
    form.status = FormStatus.ACTIVE.value
    
    # Audit
    await write_audit_entry(
        session=session,
        actor=user_id,
        actor_type="admin",
        action="version_published",
        target=form_id,
        version=version,
        details=f"Published version {version}",
        org_id=form.org_id
    )
    
    await session.commit()
    return form_version
```

## Example 7: Granting Consent (Citizen Operation)

```python
async def grant_consent(
    form_id: str,
    consent_data: ConsentGrantSchema,
    token_data: dict = Depends(require_permission(Permission.GRANT_CONSENT)),
    session: AsyncSession = Depends(get_db_session)
):
    """Grant consent to a form."""
    user_id = token_data["sub"]
    dek = get_dek()
    
    # Get form and version
    form = await session.get(ConsentForm, form_id)
    version = form.active_version
    
    # Hash IP and User-Agent (never store raw values)
    ip_hash = sha256_hash(consent_data.ip_address)
    ua_hash = sha256_hash(consent_data.user_agent)
    
    # Encrypt optional fields if provided
    optional_encrypted = None
    if consent_data.optional_fields:
        import json
        optional_json = json.dumps(consent_data.optional_fields)
        optional_encrypted = encrypt_field(optional_json, dek)
    
    # Create consent record
    consent = DpdpConsent(
        user_id=user_id,
        form_id=form_id,
        version=version,
        status=ConsentStatus.GRANTED.value,
        channel=consent_data.channel or Channel.WEB.value,
        optional_fields=optional_encrypted,
        ip_hash=ip_hash,
        user_agent_hash=ua_hash,
        granted_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=int(form.expiry_days))
    )
    
    # Generate receipt token
    receipt_payload = {
        "consent_id": consent.id,
        "form_id": form_id,
        "user_id": user_id,
        "granted_at": datetime.now(UTC).isoformat(),
        "expires_at": consent.expires_at.isoformat()
    }
    from app.core.security.crypto import hmac_sha256_sign, get_hmac_key
    consent.receipt_token = hmac_sha256_sign(receipt_payload, get_hmac_key())
    
    session.add(consent)
    await session.flush()
    
    # Audit
    await write_audit_entry(
        session=session,
        actor=user_id,
        actor_type="user",
        action="consent_granted",
        target=form_id,
        version=version,
        details=f"User granted consent via {consent.channel}",
        org_id=form.org_id
    )
    
    await session.commit()
    return consent
```

## Key Patterns

### Pattern 1: Always Hash PII for Lookups
```python
# Never do this:
user = await session.scalar(
    select(DpdpUser).where(DpdpUser.email == encrypted_email)
)

# Do this instead:
user = await session.scalar(
    select(DpdpUser).where(DpdpUser.email_hash == sha256_hash(plain_email))
)
```

### Pattern 2: Always Audit Sensitive Operations
```python
# After any state-changing operation
await write_audit_entry(
    session=session,
    actor=user_id,
    actor_type="admin",  # or "user" or "system"
    action="action_name",
    target=resource_id,
    version=version_if_applicable,
    details=human_readable_description,
    org_id=org_id
)
```

### Pattern 3: Check Permissions at Route Entry
```python
async def sensitive_endpoint(
    token_data: dict = Depends(require_permission(Permission.SPECIFIC_PERMISSION)),
    session: AsyncSession = Depends(get_db_session)
):
    # If we reach here, permission is already checked
    # token_data["sub"] = user ID
    # token_data["org_id"] = organization ID
    # token_data["role"] = user role
    pass
```

### Pattern 4: Decrypt Only When Needed
```python
# Don't decrypt everything
# users = [decrypt_field(u.email, dek) for u in all_users]  # WRONG

# Only decrypt what you need
dek = get_dek()
user = await session.get(DpdpUser, user_id)
email = decrypt_field(user.email, dek)
```

## Role Permission Quick Reference

| Role | Can Create Forms | Can Approve Forms | Can View Consents | Can Export Audit |
|------|------------------|------------------|-------------------|-----------------|
| Super Admin | ✓ | ✓ | ✓ | ✓ |
| Org Admin | ✓ | ✓ | ✓ | ✓ |
| Form Editor | ✓ | ✗ | ✗ | ✗ |
| DPO Reviewer | ✗ | ✓ | ✓ | ✓ |
| Read-Only | ✗ | ✗ | ✓ | ✗ |
| Citizen | ✗ | ✗ | Own | ✗ |
| System Service | ✗ | ✗ | ✓ | ✗ |

## Testing Your Service Layer

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.db.base import Base

@pytest.fixture
async def test_session():
    # Use in-memory SQLite for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = AsyncSession(engine, expire_on_commit=False)
    yield async_session
    await async_session.close()

@pytest.mark.asyncio
async def test_create_form(test_session):
    org = Org(id="test-org", name="Test Org")
    test_session.add(org)
    await test_session.flush()
    
    form = ConsentForm(
        id="test-form",
        org_id=org.id,
        name="Test Form",
        code="TEST001",
        purpose="Testing"
    )
    test_session.add(form)
    await test_session.commit()
    
    result = await test_session.get(ConsentForm, "test-form")
    assert result.name == "Test Form"
```

---

**Ready to implement services on the DPDP foundation!**
