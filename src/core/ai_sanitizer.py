"""AI sanitizer: masks personal data before sending to external AI."""

from dataclasses import dataclass
import re


PHONE_RE = re.compile(r"(?:\+7|8)?\s*[\d\-\s()]{7,}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class SanitizedText:
    original: str
    sanitized: str


class AiSanitizer:
    """Simple sanitizer that can optionally mask personal data."""

    def __init__(self, allow_personal_data: bool = False) -> None:
        self.allow_personal_data = allow_personal_data

    def sanitize(self, text: str) -> SanitizedText:
        if self.allow_personal_data:
            # Pass-through mode: keep text as is (assuming proper consents and compliant provider).
            return SanitizedText(original=text, sanitized=text)

        masked = PHONE_RE.sub("[PHONE]", text)
        masked = EMAIL_RE.sub("[EMAIL]", masked)
        return SanitizedText(original=text, sanitized=masked)

