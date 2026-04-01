"""Slug helpers for public URLs (ASCII, SEO-friendly)."""

from __future__ import annotations

import re

_RU = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify_ascii(value: str, *, max_len: int = 120) -> str:
    """
    Best-effort slugify:
    - transliterates RU letters
    - keeps [a-z0-9-]
    - collapses separators to single '-'
    """
    s = (value or "").strip().lower()
    if not s:
        return ""
    out = []
    for ch in s:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            out.append(ch)
            continue
        if ch in _RU:
            out.append(_RU[ch])
            continue
        if ch in {" ", "_", "-", ".", "/", "\\"}:
            out.append("-")
            continue
        # drop any other character
    slug = "".join(out)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:max_len]


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(slug: str) -> bool:
    s = (slug or "").strip().lower()
    if not (3 <= len(s) <= 120):
        return False
    return bool(_SLUG_RE.match(s))

