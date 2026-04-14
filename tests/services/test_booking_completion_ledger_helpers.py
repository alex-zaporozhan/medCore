"""LEAD B2: unit tests for ERP visit payload helpers (amounts + payment source mapping)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.services.booking_completion_service import (
    _erp_visit_payment_source,
    _net_visit_ledger_amount,
)
from src.domain.entities.payment import Payment


def _payment(*, provider: str, amount: Decimal = Decimal("150.00")) -> Payment:
    return Payment(
        id=uuid4(),
        clinic_id=uuid4(),
        booking_id=uuid4(),
        provider=provider,
        provider_payment_id=f"ext-{uuid4().hex[:8]}",
        amount=amount,
        status="succeeded",
    )


def test_net_visit_ledger_amount_prefers_payment_over_wallet() -> None:
    p = _payment(provider="yookassa", amount=Decimal("99.00"))
    assert (
        _net_visit_ledger_amount(
            services_amount=Decimal("1000"),
            wallet_spent_amount=Decimal("200"),
            payment=p,
        )
        == Decimal("99.00")
    )


def test_net_visit_ledger_amount_wallet_reduces_list_when_no_payment() -> None:
    assert (
        _net_visit_ledger_amount(
            services_amount=Decimal("1000"),
            wallet_spent_amount=Decimal("200"),
            payment=None,
        )
        == Decimal("800")
    )


def test_net_visit_ledger_amount_no_wallet() -> None:
    assert (
        _net_visit_ledger_amount(
            services_amount=Decimal("500"),
            wallet_spent_amount=Decimal("0"),
            payment=None,
        )
        == Decimal("500")
    )


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        ("yookassa", "acquiring"),
        ("YOOKASSA", "acquiring"),
        ("stripe", "acquiring"),
        ("cash", "cash"),
        ("manual_cash", "cash"),
        ("deposit", "deposit"),
        ("unknown_gateway", "other"),
    ],
)
def test_erp_visit_payment_source_mapping(provider: str, expected: str) -> None:
    assert _erp_visit_payment_source(_payment(provider=provider)) == expected
