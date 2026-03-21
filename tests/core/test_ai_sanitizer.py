import pytest

from uuid import uuid4

from src.application.ai.tokenization import make_patient_token
from src.core.ai_sanitizer import AiSanitizer


def test_ai_sanitizer_masks_phone_and_email_when_not_allowed():
    sanitizer = AiSanitizer(allow_personal_data=False)
    text = "Мой телефон +7 900 123-45-67 и почта test@example.com"

    result = sanitizer.sanitize(text)

    assert "+7 900 123-45-67" not in result.sanitized
    assert "test@example.com" not in result.sanitized
    assert "[PHONE]" in result.sanitized or "[EMAIL]" in result.sanitized


def test_ai_sanitizer_pass_through_when_allowed():
    sanitizer = AiSanitizer(allow_personal_data=True)
    text = "Мой телефон +7 900 123-45-67 и почта test@example.com"

    result = sanitizer.sanitize(text)

    assert result.sanitized == text


def test_ai_sanitizer_preserves_tokens_while_masking_personal_data():
    sanitizer = AiSanitizer(allow_personal_data=False)
    patient_id = uuid4()
    token = make_patient_token(patient_id)
    text = f"Пациент {token}, телефон +7 900 123-45-67 и email test@example.com"

    result = sanitizer.sanitize(text)

    # Personal data must be masked
    assert "+7 900 123-45-67" not in result.sanitized
    assert "test@example.com" not in result.sanitized

    # Token must be preserved verbatim
    assert token in result.sanitized


def test_ai_sanitizer_detect_tokens_helper():
    sanitizer = AiSanitizer(allow_personal_data=False)
    patient_id = uuid4()
    token = make_patient_token(patient_id)
    text = f"foo {token} bar"

    detected = sanitizer.detect_tokens(text)

    assert detected == [token]

