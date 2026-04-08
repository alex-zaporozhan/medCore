from src.core.api_error_codes import (
    HTTP_STATUS_DEFAULT_CODES,
    normalize_api_error_code,
)


def test_normalize_lowercase_unchanged() -> None:
    assert normalize_api_error_code("entitlement_required") == "entitlement_required"


def test_normalize_upper_snake() -> None:
    assert normalize_api_error_code("ENTITLEMENT_REQUIRED") == "entitlement_required"


def test_normalize_mixed_camel() -> None:
    assert normalize_api_error_code("CAPTCHA_REQUIRED") == "captcha_required"


def test_normalize_kebab() -> None:
    assert normalize_api_error_code("bad-request") == "bad_request"


def test_status_defaults_are_lower_snake() -> None:
    for c in HTTP_STATUS_DEFAULT_CODES.values():
        assert c == c.lower()
        assert " " not in c
