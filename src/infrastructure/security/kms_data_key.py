"""Optional AWS KMS envelope data-key helpers (P1-3 foundation).

When ``settings.aws_kms_key_id`` is set, callers can generate a symmetric data key
wrapped by KMS and later decrypt the ciphertext blob. Existing Fernet-at-rest
paths in ``src/core/encryption.py`` remain unchanged until explicitly migrated.
"""

from __future__ import annotations

import base64
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)


def kms_data_key_enabled() -> bool:
    return bool((settings.aws_kms_key_id or "").strip())


def generate_envelope_data_key() -> tuple[bytes, bytes]:
    """Return ``(plaintext_data_key_32_bytes, ciphertext_blob)`` for AES-256 envelope.

    Raises ``RuntimeError`` if KMS is not configured or boto3/KMS call fails.
    """
    key_id = (settings.aws_kms_key_id or "").strip()
    if not key_id:
        raise RuntimeError("aws_kms_key_id is not configured")

    import boto3  # lazy: heavy import

    client = boto3.client("kms")
    resp = client.generate_data_key(KeyId=key_id, KeySpec="AES_256")
    plain = resp.get("Plaintext")
    cipher = resp.get("CiphertextBlob")
    if not isinstance(plain, (bytes, bytearray)) or not isinstance(cipher, (bytes, bytearray)):
        raise RuntimeError("KMS generate_data_key returned unexpected payload")
    return bytes(plain), bytes(cipher)


def decrypt_envelope_data_key(ciphertext_blob: bytes) -> bytes:
    """Decrypt a ciphertext blob previously returned by ``generate_envelope_data_key``."""
    import boto3

    client = boto3.client("kms")
    resp = client.decrypt(CiphertextBlob=ciphertext_blob)
    plain = resp.get("Plaintext")
    if not isinstance(plain, (bytes, bytearray)):
        raise RuntimeError("KMS decrypt returned unexpected payload")
    return bytes(plain)


def encode_ciphertext_blob(blob: bytes) -> str:
    """Stable storage encoding for ciphertext blobs."""
    return base64.b64encode(blob).decode("ascii")
