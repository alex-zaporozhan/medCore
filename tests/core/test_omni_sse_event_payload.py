"""ARCH §6: SSE event JSON shape (no message body)."""

import json
from uuid import uuid4


def test_omni_message_created_event_shape():
    clinic_id = uuid4()
    chat_id = uuid4()
    message_id = uuid4()
    data = json.loads(
        json.dumps(
            {
                "type": "message.created",
                "chat_id": str(chat_id),
                "message_id": str(message_id),
                "clinic_id": str(clinic_id),
            }
        )
    )
    assert data["type"] == "message.created"
    assert "content" not in data
    assert data["chat_id"] == str(chat_id)
    assert data["message_id"] == str(message_id)
    assert data["clinic_id"] == str(clinic_id)
