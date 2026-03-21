"""Opaque cursor encoding for CRM Kanban (created_at DESC, id DESC)."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone
from uuid import UUID


def encode_lead_cursor(created_at: datetime, lead_id: UUID) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {"ca": created_at.isoformat(), "i": str(lead_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_lead_cursor(token: str) -> tuple[datetime, UUID]:
    padded = token + "=" * ((4 - len(token) % 4) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_cursor") from exc
    ca_raw = data.get("ca")
    i_raw = data.get("i")
    if not isinstance(ca_raw, str) or not isinstance(i_raw, str):
        raise ValueError("invalid_cursor")
    ca = datetime.fromisoformat(ca_raw)
    if ca.tzinfo is None:
        ca = ca.replace(tzinfo=timezone.utc)
    return ca, UUID(i_raw)
