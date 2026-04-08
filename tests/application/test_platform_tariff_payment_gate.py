"""Unit tests: platform tariff snapshot gate (billing_period)."""

import pytest

from src.application.services.platform_tariff_payment_gate import (
    BILLING_PERIOD_ANNUAL,
    BILLING_PERIOD_MONTHLY,
    parse_billing_period_from_snapshot,
)


def test_parse_billing_period_absent_means_none():
    assert parse_billing_period_from_snapshot({}) is None
    assert parse_billing_period_from_snapshot({"plan_slug": "x"}) is None


def test_parse_billing_period_monthly_annual_case_insensitive():
    assert parse_billing_period_from_snapshot({"billing_period": "Monthly"}) == BILLING_PERIOD_MONTHLY
    assert parse_billing_period_from_snapshot({"billing_period": "ANNUAL"}) == BILLING_PERIOD_ANNUAL


def test_parse_billing_period_invalid_raises():
    with pytest.raises(ValueError, match="invalid_billing_period"):
        parse_billing_period_from_snapshot({"billing_period": "weekly"})
