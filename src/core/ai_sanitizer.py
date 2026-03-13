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
    """Simple sanitizer that masks phone numbers and emails."""

    def sanitize(self, text: str) -> SanitizedText:
        masked = PHONE_RE.sub("[PHONE]", text)
        masked = EMAIL_RE.sub("[EMAIL]", masked)
        return SanitizedText(original=text, sanitized=masked)

