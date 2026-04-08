"""Unit tests for clinic_slug normalization on auth DTOs."""

import pytest
from pydantic import ValidationError

from src.application.dto.auth_dto import SendCodeRequest, VerifyCodeRequest


def test_send_code_clinic_slug_trim() -> None:
    r = SendCodeRequest(phone="+79001234567", clinic_slug="  my-clinic  ")
    assert r.clinic_slug == "my-clinic"


def test_send_code_clinic_slug_blank_becomes_none() -> None:
    r = SendCodeRequest(phone="+79001234567", clinic_slug="   ")
    assert r.clinic_slug is None


def test_send_code_clinic_slug_max_length() -> None:
    with pytest.raises(ValidationError):
        SendCodeRequest(phone="+79001234567", clinic_slug="x" * 121)


def test_verify_code_clinic_slug_trim() -> None:
    r = VerifyCodeRequest(phone="+79001234567", code="1234", clinic_slug="  slug  ")
    assert r.clinic_slug == "slug"
