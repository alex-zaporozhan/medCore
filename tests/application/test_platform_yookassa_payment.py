"""Unit tests: YooKassa Payment JSON → refund revocation predicate (contour B)."""

import pytest

from src.application.services.platform_yookassa_payment import (
    yookassa_payment_payload_indicates_full_refund_revocation,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"status": "refunded"}, True),
        ({"status": "chargeback", "amount": {"value": "1.00"}}, True),
        (
            {
                "status": "succeeded",
                "amount": {"value": "100.00", "currency": "RUB"},
                "refunded_amount": {"value": "100.00", "currency": "RUB"},
            },
            True,
        ),
        (
            {
                "status": "succeeded",
                "amount": {"value": "100.00", "currency": "RUB"},
                "refunded_amount": {"value": "99.99", "currency": "RUB"},
            },
            False,
        ),
        ({"status": "succeeded", "amount": {"value": "10.00"}}, False),
        ({"status": "canceled"}, False),
        ({"status": "pending"}, False),
    ],
)
def test_yookassa_full_refund_revocation_predicate(payload: dict, expected: bool) -> None:
    assert yookassa_payment_payload_indicates_full_refund_revocation(payload) is expected
