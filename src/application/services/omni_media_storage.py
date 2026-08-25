"""Файлы для сообщений omnichannel (админская загрузка + доставка в PWA/Telegram).

Хранение: тот же корень, что и staff/clinic chat (`staff_chat_upload_root`), подпуть `{clinic_id}/omni/…`.
Метаданные — JSON в `omni_messages.source_metadata`, ключи `omni_files`, `clinic_chat_bridge`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from uuid import UUID

from src.core.config import settings

OMNI_FILES_META_KEY = "omni_files"
CLINIC_CHAT_BRIDGE_META_KEY = "clinic_chat_bridge"


def sanitize_omni_filename(name: str) -> str:
    base = os.path.basename(name or "file")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:200] or "file"


def _normalize_mime(content_type: str) -> str:
    return (content_type or "").split(";")[0].strip().lower()


def sniff_omni_upload_mime(filename: str, content_type: str) -> str:
    """Resolve MIME for uploads when the browser sends empty or application/octet-stream."""
    ct = _normalize_mime(content_type)
    if ct and ct != "application/octet-stream":
        return ct

    fn = (filename or "").lower()
    if fn.endswith(".webm"):
        return "audio/webm"
    if fn.endswith(".ogg"):
        return "audio/ogg"
    if fn.endswith(".mp3"):
        return "audio/mpeg"
    if fn.endswith(".m4a"):
        return "audio/mp4"
    if fn.endswith(".wav"):
        return "audio/wav"

    return ct or "application/octet-stream"


def is_omni_svg_upload(filename: str, sniffed_content_type: str) -> bool:
    """SC1: deny SVG by filename suffix and by resolved MIME."""
    fn = (filename or "").lower()
    ct = _normalize_mime(sniffed_content_type)
    return fn.endswith(".svg") or fn.endswith(".svgz") or ct in {"image/svg+xml", "image/svg"}


def allowed_omni_upload_mime(content_type: str) -> bool:
    ct = _normalize_mime(content_type)
    # SECURITY: forbid SVG (stored XSS) and avoid broad image/* allowlists.
    if ct in {"image/svg+xml", "image/svg"}:
        return False
    if ct.startswith("audio/"):
        return True
    if ct in {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/gif",
        "image/webp",
        "image/avif",
    }:
        return True
    return ct in (
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "video/webm",
    )


def save_omni_upload(clinic_id: UUID, attachment_id: UUID, file_name: str, raw: bytes) -> str:
    """Сохранить байты; вернуть относительный путь от `staff_chat_upload_root`."""
    safe = sanitize_omni_filename(file_name)
    rel = f"{clinic_id}/omni/{attachment_id}_{safe}"
    fs_path = Path(settings.staff_chat_upload_root) / rel.replace("/", os.sep)
    fs_path.parent.mkdir(parents=True, exist_ok=True)
    fs_path.write_bytes(raw)
    return rel.replace("\\", "/")


def read_omni_file_bytes(storage_rel: str) -> bytes | None:
    path = Path(settings.staff_chat_upload_root) / storage_rel.replace("/", os.sep)
    if not path.is_file():
        return None
    return path.read_bytes()


def find_omni_file_meta(source_metadata: dict | None, attachment_id: UUID) -> dict | None:
    if not isinstance(source_metadata, dict):
        return None
    files = source_metadata.get(OMNI_FILES_META_KEY)
    if not isinstance(files, list):
        return None
    sid = str(attachment_id)
    for item in files:
        if isinstance(item, dict) and str(item.get("id") or "") == sid:
            return item
    return None
