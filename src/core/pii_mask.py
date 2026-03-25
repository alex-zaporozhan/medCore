"""Маскирование PII в строках логов (SME §2.4)."""

import re

# Телефоны: +7/8 и 10–11 цифр подряд после префикса (упрощённо для RU).
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+7|8|7)[\s\-]?(?:\(?\d{3}\)?[\s\-]?)?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"
)


def mask_phones_in_text(text: str) -> str:
    """Заменяет распознанные телефоны на маску, сохраняя длину блока грубо."""
    def _sub(m: re.Match[str]) -> str:
        s = m.group(0)
        if len(s) <= 6:
            return "***"
        return s[:3] + "***" + s[-2:]

    return _PHONE_RE.sub(_sub, text)


def mask_pii_value(value: object) -> object:
    """Рекурсивно маскирует строки; dict/list проходятся поверхностно."""
    if isinstance(value, str):
        return mask_phones_in_text(value)
    if isinstance(value, dict):
        return {k: mask_pii_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_pii_value(v) for v in value]
    return value
