"""
Compatibility repository alias for boilerplate naming parity.
"""

from app.repositories.api_credential import ApiCredentialRepository


class ApiKeyRepository(ApiCredentialRepository):
    pass


__all__ = ["ApiKeyRepository"]
