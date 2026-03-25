"""Security utilities for JWT tokens (PyJWT, HS256 — см. settings.jwt_algorithm)."""

from datetime import timedelta
from typing import Any, Dict, cast

import jwt

from src.core.config import settings
from src.core.datetime_utils import utc_now


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = utc_now()
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))

    to_encode.update({"iat": now, "exp": expire})

    return cast(
        str,
        jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        ),
    )


def parse_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token, returning payload claims."""
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    return cast(Dict[str, Any], payload)

