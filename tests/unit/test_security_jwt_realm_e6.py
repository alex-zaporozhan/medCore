"""1a-E6: iss/aud for tenant and platform-founder JWT (no DB)."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from src.core.config import settings
from src.core.security import (
    JwtClaimValidationError,
    create_access_token,
    create_platform_founder_access_token,
    create_platform_founder_mfa_token,
    parse_access_token,
    parse_platform_founder_access_token,
    parse_platform_founder_mfa_token,
    parse_tenant_access_token_for_request_context,
)


def test_tenant_admin_roundtrip_iss_aud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    aid = uuid4()
    token = create_access_token(
        {"type": "admin", "sub": str(aid)},
        expires_delta=timedelta(minutes=5),
    )
    payload = parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    assert payload["iss"] == settings.jwt_issuer_tenant
    assert payload["aud"] == settings.jwt_audience_admin
    assert payload["type"] == "admin"


def test_tenant_patient_roundtrip_iss_aud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    pid = uuid4()
    token = create_access_token(
        {"role": "patient", "sub": str(pid)},
        expires_delta=timedelta(minutes=5),
    )
    payload = parse_access_token(token, expected_audience=settings.jwt_audience_patient)
    assert payload["aud"] == settings.jwt_audience_patient


def test_tenant_rejects_wrong_audience_when_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    token = create_access_token(
        {"type": "admin", "sub": str(uuid4())},
        expires_delta=timedelta(minutes=5),
        audience=settings.jwt_audience_patient,
    )
    with pytest.raises(JwtClaimValidationError) as exc:
        parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    assert exc.value.code == "invalid_token_audience"


def test_tenant_rejects_wrong_issuer_when_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    from src.core.datetime_utils import utc_now

    expire = utc_now() + timedelta(minutes=5)
    payload = {
        "type": "admin",
        "sub": str(uuid4()),
        "iss": "evil-issuer",
        "aud": settings.jwt_audience_admin,
        "iat": utc_now(),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(JwtClaimValidationError) as exc:
        parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    assert exc.value.code == "invalid_token_issuer"


def test_tenant_legacy_token_without_iss_aud_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", True)
    from src.core.datetime_utils import utc_now

    expire = utc_now() + timedelta(minutes=5)
    payload = {
        "type": "admin",
        "sub": str(uuid4()),
        "iat": utc_now(),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    out = parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    assert out["type"] == "admin"


def test_tenant_legacy_rejects_partial_iss_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", True)
    from src.core.datetime_utils import utc_now

    expire = utc_now() + timedelta(minutes=5)
    payload = {
        "type": "admin",
        "sub": str(uuid4()),
        "iss": settings.jwt_issuer_tenant,
        "iat": utc_now(),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(JwtClaimValidationError) as exc:
        parse_access_token(token, expected_audience=settings.jwt_audience_admin)
    assert exc.value.code == "invalid_token_claims"


def test_request_context_parser_admin_patient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    token_a = create_access_token(
        {"type": "admin", "sub": str(uuid4())},
        expires_delta=timedelta(minutes=5),
    )
    pl_a = parse_tenant_access_token_for_request_context(token_a)
    assert pl_a["type"] == "admin"
    token_p = create_access_token(
        {"role": "patient", "sub": str(uuid4())},
        expires_delta=timedelta(minutes=5),
    )
    pl_p = parse_tenant_access_token_for_request_context(token_p)
    assert pl_p["role"] == "patient"


# HS256: PyJWT warns if HMAC secret is shorter than 32 bytes — use a 32+ char test key.
_FOUNDER_TEST_SECRET = "e2e-founder-key-e6-0123456789abcdef"


def test_founder_access_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", _FOUNDER_TEST_SECRET)
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    uid = uuid4()
    token = create_platform_founder_access_token(subject=uid)
    payload = parse_platform_founder_access_token(token)
    assert payload["iss"] == settings.jwt_issuer_platform
    assert payload["aud"] == settings.jwt_audience_platform_founder
    assert payload["sub"] == str(uid)


def test_founder_rejects_wrong_audience(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", _FOUNDER_TEST_SECRET)
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    from src.core.datetime_utils import utc_now

    uid = uuid4()
    expire = utc_now() + timedelta(minutes=5)
    payload = {
        "sub": str(uid),
        "type": "platform_founder",
        "iss": settings.jwt_issuer_platform,
        "aud": "wrong-audience",
        "iat": utc_now(),
        "exp": expire,
    }
    token = jwt.encode(payload, _FOUNDER_TEST_SECRET, algorithm=settings.jwt_algorithm)
    with pytest.raises(JwtClaimValidationError) as exc:
        parse_platform_founder_access_token(token)
    assert exc.value.code == "invalid_token_audience"


def test_founder_mfa_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "platform_founder_jwt_secret", _FOUNDER_TEST_SECRET)
    monkeypatch.setattr(settings, "jwt_legacy_allow_missing_iss_aud", False)
    uid = uuid4()
    token = create_platform_founder_mfa_token(subject=uid)
    payload = parse_platform_founder_mfa_token(token)
    assert payload["aud"] == settings.jwt_audience_platform_founder_mfa
