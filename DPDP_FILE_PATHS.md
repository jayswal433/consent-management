# DPDP Foundation Layer - Complete File Paths

## Core Security Modules

### app/core/security/
```
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\core\security\__init__.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\core\security\crypto.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\core\security\rbac.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\core\security\audit_writer.py
```

## ORM Models

### app/models/orm/
```
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\dpdp_enums.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\org.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\dpdp_user.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\consent_form.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\form_version.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\dpdp_consent.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\audit_log.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\nomination.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\async_job.py
```

## Modified Files

```
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\pyproject.toml
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\core\utils\constant_variable.py
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\app\models\orm\__init__.py
```

## Documentation Files

```
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\DPDP_FOUNDATION_SUMMARY.md
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\DPDP_DEVELOPER_QUICK_START.md
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\DPDP_DATA_MODEL.md
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\DPDP_BUILD_COMPLETE.txt
C:\Users\Maniljayswal\vc_projects\inhouse\everycred\everycred_backend\everycred-consent-management-backend\DPDP_FILE_PATHS.md
```

## Quick Import Guide

### For Encryption Operations
```python
from app.core.security.crypto import (
    encrypt_field,
    decrypt_field,
    sha256_hash,
    hmac_sha256_sign,
    hmac_sha256_verify,
    get_dek,
    get_hmac_key
)
```

### For RBAC
```python
from app.core.security.rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    require_permission,
    get_jwt_claims
)
```

### For Audit Logging
```python
from app.core.security.audit_writer import write_audit_entry
```

### For ORM Models
```python
from app.models.orm import (
    Org,
    DpdpUser,
    ConsentForm,
    FormVersion,
    DpdpConsent,
    AuditLog,
    Nomination,
    AsyncJob,
    ConsentStatus,
    FormStatus,
    VersionStatus,
    LegalBasis,
    Channel,
    JobStatus,
    AuditAction,
    ActorType
)
```

## Module Summary

| Module | Type | Purpose | Files |
|--------|------|---------|-------|
| crypto.py | Security | AES-256-GCM encryption, hashing, JWT signing | 1 |
| rbac.py | Security | Role-based access control with permissions | 1 |
| audit_writer.py | Security | Immutable audit logging with hash chain | 1 |
| dpdp_enums.py | Models | All DPDP enumeration types | 1 |
| org.py | Models | Organization data model | 1 |
| dpdp_user.py | Models | User data model | 1 |
| consent_form.py | Models | Consent form template model | 1 |
| form_version.py | Models | Form version history model | 1 |
| dpdp_consent.py | Models | Consent record model | 1 |
| audit_log.py | Models | Immutable audit log model | 1 |
| nomination.py | Models | Nominee registration model | 1 |
| async_job.py | Models | Async job tracking model | 1 |

**Total: 13 files created, 3 files modified, 5 documentation files**

## Environment Variables Required

Set these before running the application:

```bash
# Encryption Keys (64 hex characters each = 32 bytes)
export DPDP_DEK_HEX=0000000000000000000000000000000000000000000000000000000000000000
export DPDP_HMAC_KEY_HEX=0000000000000000000000000000000000000000000000000000000000000000

# Database Configuration (existing)
export DB_USER=root
export DB_PASSWORD=password
export DB_HOST=localhost
export DB_PORT=3306
export DB_NAME=consent_db

# JWT Configuration (existing)
export JWT_SECRET_KEY=your-secret-key
export JWT_ALGORITHM=HS256
```

## Database Migration Commands

After all files are in place, run:

```bash
# Generate migration
python -m alembic revision --autogenerate -m "add DPDP foundation layer"

# Apply migration
python -m alembic upgrade head
```

This will create 8 tables with 133 columns total in the MySQL database.

## Testing Commands

```bash
# Test all imports
python -c "from app.models.orm import *; from app.core.security import *; print('All imports OK')"

# Run integration test
python << 'EOF'
from app.core.security.crypto import encrypt_field, decrypt_field
from app.core.security.rbac import ROLE_PERMISSIONS, UserRole
from app.models.orm import *

dek = b'\x00' * 32
test = encrypt_field('hello', dek)
assert decrypt_field(test, dek) == 'hello'
assert len(ROLE_PERMISSIONS) == 7
print('Integration test passed!')
EOF
```

## Next Implementation Steps

1. **Create database migration** (Alembic)
2. **Set environment variables** (for encryption keys)
3. **Implement organization service** (using Org model)
4. **Implement user service** (using DpdpUser model)
5. **Implement form service** (using ConsentForm + FormVersion models)
6. **Implement consent service** (using DpdpConsent model)
7. **Implement audit service** (using AuditLog model)
8. **Implement user rights service** (using Nomination model)
9. **Implement async job service** (using AsyncJob model)
10. **Create API endpoints** (using require_permission dependencies)

Each service layer should:
- Import from foundation modules
- Use write_audit_entry() for all state changes
- Use require_permission() for RBAC enforcement
- Encrypt/decrypt PII using crypto functions
- Follow the established patterns in documentation

---

**All paths are absolute Windows paths. For Unix/Mac, replace backslashes with forward slashes.**
