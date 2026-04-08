"""Security utilities for JWT tokens (PyJWT, HS256 — см. settings.jwt_algorithm)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, cast
from uuid import UUID

import jwt

from src.core.config import settings
from src.core.datetime_utils import utc_now


class JwtClaimValidationError(Exception):
    """1a-E6: `iss` / `aud` validation failed after signature check."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def resolve_platform_founder_jwt_signing_key() -> str | None:
    """
    Signing key for `type=platform_founder` JWT.

    - Explicit `PLATFORM_FOUNDER_JWT_SECRET` → always used.
    - Non-production: if unset, fall back to `JWT_SECRET_KEY` (dev convenience).
    - Production: if unset, return None — do not fall back (avoid accepting admin-signed material as founder).
    """
    raw = (settings.platform_founder_jwt_secret or "").strip()
    if raw:
        return raw
    if str(settings.app_env).lower() == "production":
        return None
    return settings.jwt_secret_key


def is_platform_founder_jwt_configured() -> bool:
    """False in production when founder secret is empty; platform-founder routes should 503."""
    return resolve_platform_founder_jwt_signing_key() is not None


def _audience_matches(payload_aud: Any, expected: str) -> bool:
    if payload_aud is None:
        return False
    if isinstance(payload_aud, list):
        return expected in (str(x) for x in payload_aud)
    return str(payload_aud) == expected


def _validate_tenant_iss_aud(payload: dict[str, Any], *, expected_audience: str) -> None:
    legacy = settings.jwt_legacy_allow_missing_iss_aud
    iss = payload.get("iss")
    aud = payload.get("aud")
    if legacy and iss is None and aud is None:
        return
    if (iss is None) ^ (aud is None):
        raise JwtClaimValidationError("invalid_token_claims")
    if not legacy:
        if iss is None or aud is None:
            raise JwtClaimValidationError("invalid_token_claims")
    elif iss is None and aud is None:
        return
    if str(iss) != settings.jwt_issuer_tenant:
        raise JwtClaimValidationError("invalid_token_issuer")
    if not _audience_matches(aud, expected_audience):
        raise JwtClaimValidationError("invalid_token_audience")


def _validate_platform_founder_iss_aud(
    payload: dict[str, Any],
    *,
    expected_audience: str,
) -> None:
    legacy = settings.jwt_legacy_allow_missing_iss_aud
    iss = payload.get("iss")
    aud = payload.get("aud")
    if legacy and iss is None and aud is None:
        return
    if (iss is None) ^ (aud is None):
        raise JwtClaimValidationError("invalid_token_claims")
    if not legacy:
        if iss is None or aud is None:
            raise JwtClaimValidationError("invalid_token_claims")
    elif iss is None and aud is None:
        return
    if str(iss) != settings.jwt_issuer_platform:
        raise JwtClaimValidationError("invalid_token_issuer")
    if not _audience_matches(aud, expected_audience):
        raise JwtClaimValidationError("invalid_token_audience")


def _infer_tenant_token_audience(data: dict[str, Any]) -> str:
    if data.get("type") == "admin":
        return settings.jwt_audience_admin
    if data.get("role") == "patient":
        return settings.jwt_audience_patient
    return settings.jwt_audience_admin


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    *,
    audience: str | None = None,
) -> str:
    """Create a signed JWT access token for tenant contour (admin or patient)."""
    to_encode = data.copy()
    now = utc_now()
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    aud = audience if audience is not None else _infer_tenant_token_audience(to_encode)
    to_encode.update(
        {
            "iat": now,
            "exp": expire,
            "iss": settings.jwt_issuer_tenant,
            "aud": aud,
        }
    )

    return cast(
        str,
        jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        ),
    )


def parse_access_token(token: str, *, expected_audience: str) -> Dict[str, Any]:
    """Decode tenant JWT; enforce `iss`/`aud` unless legacy mode allows omitting both."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "require": ["exp", "iat"],
            },
        )
    except jwt.exceptions.InvalidTokenError:
        raise
    pl = cast(Dict[str, Any], payload)
    _validate_tenant_iss_aud(pl, expected_audience=expected_audience)
    return pl


def parse_tenant_access_token_for_request_context(token: str) -> Dict[str, Any]:
    """
    Decode tenant JWT and validate iss/aud using the claim `type` or `role`.
    Used by get_request_context (admin vs patient).
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "require": ["exp", "iat"],
            },
        )
    except jwt.exceptions.InvalidTokenError:
        raise
    pl = cast(Dict[str, Any], payload)
    token_type = pl.get("type") or pl.get("role")
    if token_type == "admin":
        expected = settings.jwt_audience_admin
    elif token_type == "patient":
        expected = settings.jwt_audience_patient
    else:
        raise jwt.exceptions.InvalidTokenError("unsupported tenant token type")
    _validate_tenant_iss_aud(pl, expected_audience=expected)
    return pl


def create_platform_founder_access_token(
    *,
    subject: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """JWT for platform operator (Основатель) — distinct claim `type=platform_founder`; founder signing key."""
    key = resolve_platform_founder_jwt_signing_key()
    if key is None:
        raise RuntimeError(
            "PLATFORM_FOUNDER_JWT_SECRET must be set in production to mint platform founder JWT"
        )
    minutes = settings.jwt_access_token_expire_minutes_platform_founder
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "type": "platform_founder",
        "iss": settings.jwt_issuer_platform,
        "aud": settings.jwt_audience_platform_founder,
    }
    now = utc_now()
    expire = now + (expires_delta or timedelta(minutes=minutes))
    to_encode.update({"iat": now, "exp": expire})
    return cast(
        str,
        jwt.encode(
            to_encode,
            key,
            algorithm=settings.jwt_algorithm,
        ),
    )


def parse_platform_founder_access_token(token: str) -> Dict[str, Any]:
    """Decode JWT issued for `type=platform_founder` (never uses admin key fallback in production)."""
    key = resolve_platform_founder_jwt_signing_key()
    if key is None:
        raise jwt.InvalidTokenError("platform founder jwt not configured")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "require": ["exp", "iat"],
            },
        )
    except jwt.exceptions.InvalidTokenError:
        raise
    pl = cast(Dict[str, Any], payload)
    if pl.get("type") != "platform_founder":
        raise jwt.InvalidTokenError("not a platform founder access token")
    _validate_platform_founder_iss_aud(
        pl,
        expected_audience=settings.jwt_audience_platform_founder,
    )
    return pl


def create_platform_founder_mfa_token(
    *,
    subject: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Pre-auth token after password verification when TOTP is required (1a-E3)."""
    key = resolve_platform_founder_jwt_signing_key()
    if key is None:
        raise RuntimeError(
            "PLATFORM_FOUNDER_JWT_SECRET must be set in production to mint platform founder MFA JWT"
        )
    minutes = settings.jwt_platform_founder_mfa_expire_minutes
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "type": "platform_founder_mfa",
        "iss": settings.jwt_issuer_platform,
        "aud": settings.jwt_audience_platform_founder_mfa,
    }
    now = utc_now()
    expire = now + (expires_delta or timedelta(minutes=minutes))
    to_encode.update({"iat": now, "exp": expire})
    return cast(
        str,
        jwt.encode(
            to_encode,
            key,
            algorithm=settings.jwt_algorithm,
        ),
    )


def parse_platform_founder_mfa_token(token: str) -> Dict[str, Any]:
    key = resolve_platform_founder_jwt_signing_key()
    if key is None:
        raise jwt.InvalidTokenError("platform founder jwt not configured")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_aud": False,
                "verify_iss": False,
                "require": ["exp", "iat"],
            },
        )
    except jwt.exceptions.InvalidTokenError:
        raise
    pl = cast(Dict[str, Any], payload)
    if pl.get("type") != "platform_founder_mfa":
        raise jwt.InvalidTokenError("not an mfa token")
    _validate_platform_founder_iss_aud(
        pl,
        expected_audience=settings.jwt_audience_platform_founder_mfa,
    )
    return pl
