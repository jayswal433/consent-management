from __future__ import annotations

from enum import Enum


class ConsentStatus(str, Enum):
    """Status of a consent record."""

    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    DECLINED = "declined"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class FormStatus(str, Enum):
    """Status of a consent form."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    ARCHIVED = "archived"


class VersionStatus(str, Enum):
    """Status of a form version."""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACTIVE = "active"
    ARCHIVED = "archived"


class LegalBasis(str, Enum):
    """Legal basis for data processing."""

    CONSENT = "consent"
    LEGITIMATE_INTEREST = "legitimate_interest"
    VITAL_INTEREST = "vital_interest"


class Channel(str, Enum):
    """Channel through which consent was granted."""

    WEB = "web"
    MOBILE = "mobile"
    API = "api"


class JobStatus(str, Enum):
    """Status of an async job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditAction(str, Enum):
    """Audit action types."""

    CONSENT_GRANTED = "consent_granted"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    CONSENT_DECLINED = "consent_declined"
    CONSENT_EXPIRED = "consent_expired"
    VERSION_PUBLISHED = "version_published"
    VERSION_ROLLBACK = "version_rollback"
    VERSION_SUBMITTED = "version_submitted"
    FORM_CREATED = "form_created"
    FORM_DEACTIVATED = "form_deactivated"
    FORM_ACTIVATED = "form_activated"
    ORG_CREATED = "org_created"
    ORG_OFFBOARDED = "org_offboarded"
    PII_ERASURE = "pii_erasure"
    KEY_ROTATION = "key_rotation"
    EXPORT_REQUESTED = "export_requested"
    RECONSENT_NOTIFIED = "reconsent_notified"
    AUTO_REVOKED = "auto_revoked"
    CONSENT_SUPERSEDED = "consent_superseded"
    SECURITY_EVENT = "security_event"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"


class ActorType(str, Enum):
    """Type of actor performing an action."""

    ADMIN = "admin"
    USER = "user"
    SYSTEM = "system"
