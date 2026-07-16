"""
Compatibility domain alias for boilerplate naming parity.

Maps boilerplate `ApiKeyDomain` name to existing `ApiCredentialDomain`
without changing runtime behavior.
"""

from app.models.domain.api_credential import \
    ApiCredentialDomain as ApiKeyDomain

__all__ = ["ApiKeyDomain"]
