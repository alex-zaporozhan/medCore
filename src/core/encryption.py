"""Encrypt/decrypt sensitive values (e.g. per-clinic YooKassa secret) using app secret_key."""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import settings

logger = logging.getLogger(__name__)


def _fernet_key() -> bytes:
    """Derive a valid Fernet key (32 bytes, base64) from settings.secret_key."""
    raw = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_plaintext(plain: str) -> str | None:
    """Encrypt string; return base64 ciphertext or None if empty."""
    if not plain or not plain.strip():
        return None
    try:
        f = Fernet(_fernet_key())
        return f.encrypt(plain.strip().encode()).decode()
    except Exception as e:
        logger.exception("Encryption failed: %s", e)
        raise


def decrypt_ciphertext(cipher: str | None) -> str | None:
    """Decrypt base64 ciphertext; return plaintext or None."""
    if not cipher or not cipher.strip():
        return None
    try:
        f = Fernet(_fernet_key())
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        logger.warning("Decrypt failed: invalid token (wrong key or corrupted data)")
        return None
    except Exception as e:
        logger.exception("Decryption failed: %s", e)
        return None
