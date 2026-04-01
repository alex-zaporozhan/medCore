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


def allowed_omni_upload_mime(content_type: str) -> bool:
    ct = (content_type or "").split(";")[0].strip().lower()
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
