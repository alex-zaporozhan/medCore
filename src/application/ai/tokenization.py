from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple
from uuid import UUID

import re
import uuid as _uuid


# v1 tokenization layer.
#
# Tokens encode real UUIDs directly in the string form PATIENT#<uuid>, BOOKING#<uuid>, etc.
# This keeps implementation simple and makes tokens easy to detect via regex, while still
# allowing us to later switch to an indirection table ai_token_mapping where the suffix
# will be a pseudo‑identifier instead of the real UUID. Callers should therefore treat
# the token string as an opaque handle and NOT rely on the internal UUID format.


TOKEN_PREFIX_PATIENT = "PATIENT"
TOKEN_PREFIX_BOOKING = "BOOKING"
TOKEN_PREFIX_PACKAGE = "PACKAGE"
TOKEN_PREFIX_WALLET = "WALLET"
TOKEN_PREFIX_LEAD = "LEAD"
TOKEN_PREFIX_BIRTHDATE = "BIRTHDATE"


UUID_PATTERN = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# Generic detector for all supported tokens inside free text.
TOKEN_RE = re.compile(
    rf"\b(?P<prefix>{TOKEN_PREFIX_PATIENT}|{TOKEN_PREFIX_BOOKING}|{TOKEN_PREFIX_PACKAGE}|{TOKEN_PREFIX_WALLET}|{TOKEN_PREFIX_LEAD}|{TOKEN_PREFIX_BIRTHDATE})#(?P<uuid>{UUID_PATTERN})\b"
)

# Narrow detectors for specific entity types (handy for tests / callers).
PATIENT_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_PATIENT}#(?P<uuid>{UUID_PATTERN})\b")
BOOKING_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_BOOKING}#(?P<uuid>{UUID_PATTERN})\b")
PACKAGE_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_PACKAGE}#(?P<uuid>{UUID_PATTERN})\b")
WALLET_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_WALLET}#(?P<uuid>{UUID_PATTERN})\b")
LEAD_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_LEAD}#(?P<uuid>{UUID_PATTERN})\b")
BIRTHDATE_TOKEN_RE = re.compile(rf"\b{TOKEN_PREFIX_BIRTHDATE}#(?P<uuid>{UUID_PATTERN})\b")


def make_patient_token(patient_id: UUID) -> str:
    return f"{TOKEN_PREFIX_PATIENT}#{patient_id}"


def make_booking_token(booking_id: UUID) -> str:
    return f"{TOKEN_PREFIX_BOOKING}#{booking_id}"


def make_package_token(package_id: UUID) -> str:
    return f"{TOKEN_PREFIX_PACKAGE}#{package_id}"


def make_wallet_token(wallet_id: UUID) -> str:
    return f"{TOKEN_PREFIX_WALLET}#{wallet_id}"


def make_lead_token(lead_id: UUID) -> str:
    return f"{TOKEN_PREFIX_LEAD}#{lead_id}"


_BIRTHDATE_NAMESPACE = _uuid.UUID("2e7b2d9a-9b1b-4a5f-8c3f-1d4d7b1f9f2a")


def make_birthdate_token(birth_date: str) -> str:
    """
    Return a stable token for a birth date value without exposing the date.

    Token uses uuid5(name=birth_date) so the date cannot be reconstructed from token.
    """
    value = (birth_date or "").strip()
    pseudo = _uuid.uuid5(_BIRTHDATE_NAMESPACE, value or "unknown")
    return f"{TOKEN_PREFIX_BIRTHDATE}#{pseudo}"


def _parse_token_with_expected_prefix(token: str, expected_prefix: str) -> UUID:
    """
    Internal helper to parse <PREFIX>#<uuid> tokens.

    Raises ValueError if format is invalid or prefix does not match.
    """
    if not isinstance(token, str):
        raise ValueError("Token must be a string")
    try:
        prefix, raw_uuid = token.split("#", 1)
    except ValueError as exc:
        raise ValueError("Invalid token format, expected '<TYPE>#<uuid>'") from exc

    if prefix != expected_prefix:
        raise ValueError(f"Invalid token prefix: expected '{expected_prefix}', got '{prefix}'")

    try:
        return UUID(raw_uuid)
    except ValueError as exc:
        raise ValueError("Invalid UUID inside token") from exc


def parse_patient_token(token: str) -> UUID:
    return _parse_token_with_expected_prefix(token, TOKEN_PREFIX_PATIENT)


def parse_booking_token(token: str) -> UUID:
    return _parse_token_with_expected_prefix(token, TOKEN_PREFIX_BOOKING)


def parse_package_token(token: str) -> UUID:
    return _parse_token_with_expected_prefix(token, TOKEN_PREFIX_PACKAGE)


def parse_wallet_token(token: str) -> UUID:
    return _parse_token_with_expected_prefix(token, TOKEN_PREFIX_WALLET)


def parse_lead_token(token: str) -> UUID:
    return _parse_token_with_expected_prefix(token, TOKEN_PREFIX_LEAD)


@dataclass(frozen=True)
class DetectedToken:
    """Structured representation of a token found in free text."""

    prefix: str
    id: UUID
    raw: str


def detect_tokens(text: str) -> List[DetectedToken]:
    """
    Detect all supported tokens inside arbitrary text.

    This is intentionally tolerant: it skips over invalid UUIDs instead of failing fast.
    """
    if not text:
        return []

    results: list[DetectedToken] = []
    for match in TOKEN_RE.finditer(text):
        prefix = match.group("prefix")
        raw_uuid = match.group("uuid")
        raw_token = match.group(0)
        try:
            uid = UUID(raw_uuid)
        except ValueError:
            # Skip malformed UUIDs while still allowing sanitizer to run.
            continue
        results.append(DetectedToken(prefix=prefix, id=uid, raw=raw_token))
    return results


def extract_token_strings(text: str) -> List[str]:
    """
    Convenience helper: return raw token strings as they appear in text.
    """
    return [t.raw for t in detect_tokens(text)]


def replace_tokens(
    text: str,
    replacements: Iterable[Tuple[str, str]],
) -> str:
    """
    Replace specific token strings with other strings.

    Intended to be used for id ↔ token round-trips in higher-level services.
    """
    if not text:
        return text
    result = text
    for old, new in replacements:
        if old and new and old in result:
            result = result.replace(old, new)
    return result


