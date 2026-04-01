"""Cloudflare Turnstile server-side verification (adaptive captcha)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


@dataclass(frozen=True)
class TurnstileVerifyResult:
    ok: bool
    error_codes: list[str]


async def verify_turnstile(token: str | None, *, remote_ip: str | None) -> TurnstileVerifyResult:
    """Verify Turnstile token with Cloudflare.

    Fail-closed when enabled: if enabled but misconfigured/unreachable → ok=False.
    """
    if not settings.turnstile_enabled:
        return TurnstileVerifyResult(ok=True, error_codes=[])
    if not settings.turnstile_secret_key or not settings.turnstile_secret_key.strip():
        return TurnstileVerifyResult(ok=False, error_codes=["misconfigured_secret"])
    if token is None or not token.strip():
        return TurnstileVerifyResult(ok=False, error_codes=["missing_token"])

    data = {"secret": settings.turnstile_secret_key, "response": token.strip()}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=data)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "turnstile_verify_failed",
            extra={"error": str(exc)},
        )
        return TurnstileVerifyResult(ok=False, error_codes=["verify_failed"])

    ok = bool(payload.get("success"))
    codes = payload.get("error-codes") or []
    if not isinstance(codes, list):
        codes = [str(codes)]
    return TurnstileVerifyResult(ok=ok, error_codes=[str(x) for x in codes])

