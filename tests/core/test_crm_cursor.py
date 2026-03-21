"""CRM Kanban cursor encoding."""

from datetime import datetime, timezone
from uuid import uuid4

from src.application.crm_cursor import decode_lead_cursor, encode_lead_cursor


def test_lead_cursor_roundtrip() -> None:
    uid = uuid4()
    ca = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    token = encode_lead_cursor(ca, uid)
    ca2, uid2 = decode_lead_cursor(token)
    assert uid2 == uid
    assert ca2 == ca
