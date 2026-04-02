"""AI sanitizer: masks personal data before sending to external AI."""

from dataclasses import dataclass
import re

from src.application.ai.tokenization import TOKEN_RE, extract_token_strings


# Phone regex must not match arbitrary digit-hyphen sequences. UUID segments can look
# like `8-xxxx-xxxx` and falsely match; entity tokens are shielded in sanitize() before
# PHONE_RE runs (see _shield_entity_tokens).
PHONE_RE = re.compile(r"(?:\+7|8)\s*[\d\-\s()]{7,}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Placeholders for future name/address masking (SEC roadmap).
# They are intentionally conservative and currently unused in sanitize(), so that
# enabling them later does not silently change behaviour for existing deployments.
NAME_RE = re.compile(r"")
ADDRESS_RE = re.compile(r"")

_TOKEN_SHIELD = "__AI_ENTITY_TOKEN_{}__"


def _shield_entity_tokens(text: str) -> tuple[str, list[str]]:
    """Replace PATIENT#/BOOKING#/… spans so PHONE_RE cannot corrupt UUIDs inside tokens."""
    found: list[str] = []

    def _repl(m: re.Match[str]) -> str:
        found.append(m.group(0))
        return _TOKEN_SHIELD.format(len(found) - 1)

    return TOKEN_RE.sub(_repl, text), found


def _unshield_entity_tokens(text: str, tokens: list[str]) -> str:
    out = text
    for i, raw in enumerate(tokens):
        out = out.replace(_TOKEN_SHIELD.format(i), raw)
    return out


@dataclass
class SanitizedText:
    original: str
    sanitized: str


class AiSanitizer:
    """Simple sanitizer that can optionally mask personal data.

    Policy (see ARCH_DEV_OMNI_POLICY_016 / ARCH_DEV_AI_TOKENIZATION_025):
    - when allow_personal_data is False, external AI must not see raw phones/emails;
    - tokens like PATIENT#<uuid> / BOOKING#<uuid> are preserved and can be used as
      stable references for downstream services;
    - future iterations may extend masking to names/addresses via NAME_RE/ADDRESS_RE.
    """

    def __init__(self, allow_personal_data: bool = False) -> None:
        self.allow_personal_data = allow_personal_data

    def detect_tokens(self, text: str) -> list[str]:
        """
        Detect all AI tokens in text and return them as raw strings.

        Tokens are left intact by sanitize(), even when personal data is masked.
        """
        return extract_token_strings(text)

    def sanitize(self, text: str) -> SanitizedText:
        if self.allow_personal_data:
            # Pass-through mode: keep text as is (assuming proper consents and compliant provider).
            return SanitizedText(original=text, sanitized=text)

        shielded, token_parts = _shield_entity_tokens(text)
        masked = PHONE_RE.sub("[PHONE]", shielded)
        masked = EMAIL_RE.sub("[EMAIL]", masked)
        masked = _unshield_entity_tokens(masked, token_parts)
        return SanitizedText(original=text, sanitized=masked)

