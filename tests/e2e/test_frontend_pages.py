"""
E2E: check every admin and app route on the live frontend.

Run only when frontend is served (e.g. npm run dev in frontend/) and BASE_URL is set:
  FRONTEND_E2E_URL=http://localhost:5175 poetry run pytest tests/e2e/test_frontend_pages.py -v

Install browser once: poetry run playwright install chromium
"""

import os

import pytest

FRONTEND_E2E_URL = os.environ.get("FRONTEND_E2E_URL", "").rstrip("/")

# All routes that must render without white screen or fatal error
ADMIN_PATHS = [
    "/admin",
    "/admin/schedule",
    "/admin/bookings",
    "/admin/reports",
    "/admin/doctors",
    "/admin/patients",
    "/admin/sales",
]
APP_PATHS = [
    "/app",
    "/app/booking",
    "/app/history",
    "/login",
]
LANDING_PATH = "/"

ALL_PATHS = [LANDING_PATH] + ADMIN_PATHS + APP_PATHS


@pytest.fixture(scope="module")
def frontend_base_url():
    """Live frontend base URL (CI: vite preview + FRONTEND_E2E_URL)."""
    assert FRONTEND_E2E_URL, "FRONTEND_E2E_URL must be set for browser E2E"
    return FRONTEND_E2E_URL


@pytest.mark.skipif(not FRONTEND_E2E_URL, reason="Set FRONTEND_E2E_URL and serve frontend (e.g. npm run preview)")
class TestFrontendPages:
    """Visit each frontend route and assert page loads (no white screen / fatal error)."""

    @pytest.mark.parametrize("path", ALL_PATHS)
    def test_page_loads_and_has_content(self, page, frontend_base_url, path):
        """Load path and check response is OK and body has meaningful content."""
        url = f"{frontend_base_url}{path}"
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            pytest.fail(f"{path}: failed to load — {e!s}")

        if response and response.status >= 400:
            pytest.fail(f"{path}: HTTP {response.status}")

        # SPA: same HTML for all routes; ensure root app mounted (not empty/error screen)
        content = page.content()
        assert content, f"{path}: empty response body"
        # Root div or app shell
        assert "dental" in content.lower() or "root" in content or "<div" in content, (
            f"{path}: page body looks empty or not the app (no 'dental' or root div)"
        )

    @pytest.mark.parametrize("path", ALL_PATHS)
    def test_page_no_console_errors(self, page, frontend_base_url, path):
        """Capture console errors on load; fail if any (helps debug white screen)."""
        errors = []

        def on_console(msg):
            if msg.type == "error":
                errors.append(msg.text)

        page.on("console", on_console)
        url = f"{frontend_base_url}{path}"
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            pytest.fail(f"{path}: load failed — {e!s}")

        # Filter out known non-fatal console noise (e.g. 404 source maps/assets in preview).
        fatal = [
            e
            for e in errors
            if "Uncaught" in e
            or "SyntaxError" in e
            or ("Failed to load" in e and "404" not in e and "status of 404" not in e)
        ]
        if fatal:
            pytest.fail(f"{path}: console errors: {'; '.join(fatal[:3])}")
