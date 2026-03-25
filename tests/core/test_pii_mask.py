"""Tests for PII masking in log strings (SME §2.4)."""

from src.core.pii_mask import mask_phones_in_text, mask_pii_value


def test_mask_phone_plus7() -> None:
    s = "call +7 (912) 345-67-89 now"
    out = mask_phones_in_text(s)
    assert "***" in out
    assert "345-67-89" not in out


def test_mask_pii_value_nested() -> None:
    payload = {"msg": "8 900 111-22-33", "n": 1}
    masked = mask_pii_value(payload)
    assert isinstance(masked, dict)
    assert masked["n"] == 1
    assert "***" in str(masked["msg"])
