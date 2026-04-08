"""DLQ gauge row semantics (must match SQL in refresh_platform_billing_provision_gauges)."""

import pytest

from src.application.services.platform_billing_service import signup_intent_row_matches_dead_letter_gauge


@pytest.mark.parametrize(
    ("status", "provision_dead_letter", "expected"),
    [
        ("dead_letter", False, True),
        ("reconcile_closed_manual", True, False),
        ("reconcile_closed_manual", False, False),
        ("paid", True, True),
        ("paid", False, False),
        ("provision_failed", True, True),
    ],
)
def test_dead_letter_gauge_row(
    status: str,
    provision_dead_letter: bool,
    expected: bool,
) -> None:
    assert (
        signup_intent_row_matches_dead_letter_gauge(
            status=status,
            provision_dead_letter=provision_dead_letter,
        )
        is expected
    )
