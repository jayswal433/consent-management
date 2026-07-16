from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
from typing import Any

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


def encrypt_field(plaintext: str, key: bytes) -> str:
    """
    Encrypt a field using AES-256-GCM.

    Generates a random 12-byte IV, encrypts the plaintext, and returns
    Base64(IV + TAG + Ciphertext) where TAG is the 16-byte GCM auth tag.

    Args:
        plaintext: The string to encrypt.
        key: 32-byte encryption key (256 bits).

    Returns:
        Base64-encoded string of IV + TAG + Ciphertext.

    Raises:
        ValueError: If key is not 32 bytes.
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")

    iv = os.urandom(12)
    cipher = AESGCM(key)
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext = cipher.encrypt(iv, plaintext_bytes, None)

    combined = iv + ciphertext
    return base64.b64encode(combined).decode("utf-8")


def decrypt_field(ciphertext_b64: str, key: bytes) -> str:
    """
    Decrypt a field encrypted with encrypt_field().

    Decodes the Base64 string, extracts IV (12 bytes), TAG (16 bytes),
    and ciphertext, then decrypts using AES-256-GCM.

    Args:
        ciphertext_b64: Base64-encoded string of IV + TAG + Ciphertext.
        key: 32-byte encryption key (256 bits).

    Returns:
        Decrypted plaintext string.

    Raises:
        ValueError: If decryption fails or key is not 32 bytes.
    """
    if len(key) != 32:
        raise ValueError(f"Key must be 32 bytes, got {len(key)}")

    try:
        combined = base64.b64decode(ciphertext_b64)
        iv = combined[:12]
        ciphertext = combined[12:]

        cipher = AESGCM(key)
        plaintext_bytes = cipher.decrypt(iv, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}") from e


def sha256_hash(value: str, salt: str = "") -> str:
    """
    Compute SHA-256 hash of a value with optional salt.

    Args:
        value: The string to hash.
        salt: Optional salt prepended to the value before hashing.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    combined = (salt + value).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def hmac_sha256_sign(payload: dict[str, Any], secret: bytes) -> str:
    """
    Sign a payload using HMAC-SHA256 and return a compact JWT.

    Args:
        payload: Dictionary to encode as JWT payload.
        secret: Secret key for signing.

    Returns:
        JWT token string.
    """
    return jwt.encode(payload, secret, algorithm="HS256")


def hmac_sha256_verify(token: str, secret: bytes) -> dict[str, Any]:
    """
    Verify and decode a JWT signed with HS256.

    Args:
        token: JWT token string.
        secret: Secret key for verification.

    Returns:
        Decoded payload dictionary.

    Raises:
        ValueError: If verification fails.
    """
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidSignatureError as e:
        raise ValueError("Invalid token signature") from e
    except jwt.DecodeError as e:
        raise ValueError("Failed to decode token") from e


def get_dek() -> bytes:
    """
    Get the Data Encryption Key (DEK) from environment.

    Reads DPDP_DEK_HEX environment variable, which should be a 64-character
    hex string (256 bits = 32 bytes).

    Returns:
        32-byte encryption key.

    Raises:
        ValueError: If DEK is not 64 hex characters.
    """
    dek_hex = os.getenv("DPDP_DEK_HEX", "")

    if not dek_hex:
        logger.warning(
            "DPDP_DEK_HEX not set; using a warning key. "
            "Set DPDP_DEK_HEX in production."
        )
        dek_hex = "0" * 64

    if len(dek_hex) != 64:
        raise ValueError(
            f"DPDP_DEK_HEX must be 64 hex characters (256 bits), "
            f"got {len(dek_hex)}"
        )

    try:
        return bytes.fromhex(dek_hex)
    except ValueError as e:
        raise ValueError("DPDP_DEK_HEX must contain valid hex characters") from e


def get_hmac_key() -> bytes:
    """
    Get the HMAC key from environment.

    Reads DPDP_HMAC_KEY_HEX environment variable, which should be a hex string.
    If not set, defaults to a warning key.

    Returns:
        HMAC key as bytes.
    """
    hmac_hex = os.getenv("DPDP_HMAC_KEY_HEX", "")

    if not hmac_hex:
        logger.warning(
            "DPDP_HMAC_KEY_HEX not set; using a warning key. "
            "Set DPDP_HMAC_KEY_HEX in production."
        )
        hmac_hex = "0" * 64

    try:
        return bytes.fromhex(hmac_hex)
    except ValueError as e:
        raise ValueError(
            "DPDP_HMAC_KEY_HEX must contain valid hex characters"
        ) from e
