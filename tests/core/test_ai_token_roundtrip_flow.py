from uuid import uuid4

from src.application.ai.tokenization import make_patient_token, parse_patient_token
from src.core.ai_sanitizer import AiSanitizer


def test_id_token_roundtrip_through_sanitizer_text_flow():
    """End-to-end: id -> token -> text -> sanitize -> detect -> id."""
    patient_id = uuid4()
    token = make_patient_token(patient_id)

    # Text that would be sent to AI (contains both token and personal data).
    text = f"Пациент {token}, телефон +7 900 123-45-67."

    sanitizer = AiSanitizer(allow_personal_data=False)
    sanitized = sanitizer.sanitize(text)

    # Phone must be masked.
    assert "+7 900 123-45-67" not in sanitized.sanitized
    assert "[PHONE]" in sanitized.sanitized

    # Token must survive as stable handle and be parseable back into UUID.
    tokens = sanitizer.detect_tokens(sanitized.sanitized)
    assert tokens == [token]
    roundtrip_id = parse_patient_token(tokens[0])
    assert roundtrip_id == patient_id

