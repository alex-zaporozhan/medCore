"""Stickers API: default set for chat (classic emoji set, Apple-style)."""

from fastapi import APIRouter

router = APIRouter(prefix="/stickers", tags=["stickers"])

_BASE = "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.0.1/img/apple/64"

# Classic emoji set (smileys, gestures, hearts — like Android/iOS). Old keys kept for backward compat.
DEFAULT_STICKER_SET: list[dict[str, str]] = [
    {"key": "default/smile_01", "url": f"{_BASE}/1f600.png"},
    {"key": "default/smile_02", "url": f"{_BASE}/1f603.png"},
    {"key": "default/smile_03", "url": f"{_BASE}/1f604.png"},
    {"key": "default/heart", "url": f"{_BASE}/2764-fe0f.png"},
    {"key": "default/thumbsup", "url": f"{_BASE}/1f44d.png"},
    {"key": "default/1f601", "url": f"{_BASE}/1f601.png"},
    {"key": "default/1f606", "url": f"{_BASE}/1f606.png"},
    {"key": "default/1f605", "url": f"{_BASE}/1f605.png"},
    {"key": "default/1f602", "url": f"{_BASE}/1f602.png"},
    {"key": "default/1f923", "url": f"{_BASE}/1f923.png"},
    {"key": "default/1f60a", "url": f"{_BASE}/1f60a.png"},
    {"key": "default/1f607", "url": f"{_BASE}/1f607.png"},
    {"key": "default/1f642", "url": f"{_BASE}/1f642.png"},
    {"key": "default/1f643", "url": f"{_BASE}/1f643.png"},
    {"key": "default/1f609", "url": f"{_BASE}/1f609.png"},
    {"key": "default/1f60d", "url": f"{_BASE}/1f60d.png"},
    {"key": "default/1f618", "url": f"{_BASE}/1f618.png"},
    {"key": "default/1f49c", "url": f"{_BASE}/1f49c.png"},
    {"key": "default/1f44e", "url": f"{_BASE}/1f44e.png"},
    {"key": "default/1f44c", "url": f"{_BASE}/1f44c.png"},
    {"key": "default/270c", "url": f"{_BASE}/270c-fe0f.png"},
    {"key": "default/1f91d", "url": f"{_BASE}/1f91d.png"},
    {"key": "default/1f64c", "url": f"{_BASE}/1f64c.png"},
    {"key": "default/1f4aa", "url": f"{_BASE}/1f4aa.png"},
    {"key": "default/1f389", "url": f"{_BASE}/1f389.png"},
]


@router.get("/sets")
async def get_sticker_sets() -> dict:
    """Return available sticker sets (key + url per sticker)."""
    return {
        "sets": {
            "default": DEFAULT_STICKER_SET,
        }
    }
