"""Encrypt TOTP shared secrets at rest (1a-E3) — key derived from SECRET_KEY."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from src.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        f"dental-booking:platform-founder-totp:{settings.secret_key}".encode()
    ).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_totp_secret(plain_base32: str) -> str:
    return _fernet().encrypt(plain_base32.encode("utf-8")).decode("ascii")


def decrypt_totp_secret(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
