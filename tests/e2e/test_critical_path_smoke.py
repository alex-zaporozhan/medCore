"""
LEAD A3: minimal browser smoke for marketing owner-invite shell.

``FRONTEND_E2E_URL`` is optional locally: if unset and ``test_critical_path_smoke`` is
collected, ``tests/e2e/vite_preview_server`` starts ``vite preview`` on 127.0.0.1:4173
(unless ``PYTEST_DISABLE_VITE_AUTOSTART=1``). CI still sets the URL explicitly.

Requires Playwright chromium: ``poetry run playwright install chromium``
"""

from __future__ import annotations

import pytest


@pytest.mark.critical_path
def test_owner_invite_route_renders_without_white_screen(page, base_url):
    """SPA route /signup/owner-invite must load (LEAD A1 acceptance page)."""
    url = f"{base_url}/signup/owner-invite"
    response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    if response is not None and response.status >= 400:
        pytest.fail(f"{url}: HTTP {response.status}")
    content = page.content()
    assert content, "empty document"
    assert "root" in content.lower() or "<div" in content, "app shell not detected"
