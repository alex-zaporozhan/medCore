"""E2E / Playwright: shared fixtures for ``tests/e2e``."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session")
def base_url():
    """Base URL for browser tests (CI: workflow sets ``FRONTEND_E2E_URL``; local: auto vite preview)."""
    u = (os.environ.get("FRONTEND_E2E_URL") or "").strip().rstrip("/")
    if not u:
        if os.environ.get("CRITICAL_PATH_CI", "").strip().lower() in ("1", "true", "yes"):
            pytest.fail(
                "CRITICAL_PATH_CI: FRONTEND_E2E_URL must be set for Playwright "
                "(vite autostart should have run in collection — check logs)"
            )
        pytest.skip(
            "FRONTEND_E2E_URL not set (set explicitly or unset PYTEST_DISABLE_VITE_AUTOSTART for auto preview)"
        )
    return u
