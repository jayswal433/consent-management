"""
API key utilities module.
"""

import hashlib
import secrets


def generate_api_key(prefix: str = "ak_") -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
