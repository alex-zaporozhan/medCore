"""1b-E1: public platform signup checkout (intent + YooKassa URL)."""

import pytest
from httpx import AsyncClient

from src.core.config import settings
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

CHECKOUT = "/api/v1/public/platform/signup/checkout"


@pytest.mark.asyncio
async def test_public_platform_checkout_happy_path_stub_yookassa(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "yookassa_shop_id", "test-shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "test-secret")
    from src.infrastructure.external_apis import yookassa_client as yk_mod

    def fake_create_platform_subscription_payment(self, *args, **kwargs):
        return "prov-pay-test-1", "https://pay.example/yk"

    monkeypatch.setattr(
        yk_mod.YooKassaClient,
        "create_platform_subscription_payment",
        fake_create_platform_subscription_payment,
    )

    r = await client.post(
        CHECKOUT,
        json={
            "email": "buyer@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("payment_url") == "https://pay.example/yk"
    assert data.get("signup_intent_id")
    assert data.get("amount_rub")


@pytest.mark.asyncio
async def test_public_platform_checkout_unknown_plan(client: AsyncClient):
    r = await client.post(
        CHECKOUT,
        json={
            "email": "buyer@example.com",
            "plan_slug": "does_not_exist_plan_slug",
            "billing_period": "annual",
        },
    )
    assert r.status_code == 400
    j = r.json()
    assert j.get("code") == "unknown_plan_slug"


@pytest.mark.asyncio
async def test_public_platform_checkout_yookassa_not_configured(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "yookassa_shop_id", "")
    monkeypatch.setattr(settings, "yookassa_secret_key", "")
    r = await client.post(
        CHECKOUT,
        json={
            "email": "buyer@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
        },
    )
    assert r.status_code == 503
    j = r.json()
    assert j.get("code") == "yookassa_not_configured"


@pytest.mark.asyncio
async def test_public_platform_checkout_rate_limit_by_ip(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from src.main import app

    monkeypatch.setattr(settings, "yookassa_shop_id", "test-shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "test-secret")
    monkeypatch.setattr(settings, "rate_public_platform_checkout_ip_limit", 2)
    monkeypatch.setattr(settings, "rate_public_platform_checkout_ip_window_seconds", 600)
    from src.infrastructure.external_apis import yookassa_client as yk_mod

    _seq = 0

    def fake_create_platform_subscription_payment(self, *args, **kwargs):
        nonlocal _seq
        _seq += 1
        return f"prov-pay-ip-{_seq}", "https://pay.example/yk"

    monkeypatch.setattr(
        yk_mod.YooKassaClient,
        "create_platform_subscription_payment",
        fake_create_platform_subscription_payment,
    )

    class _IpOnlyRl:
        def __init__(self) -> None:
            self.ip_hits = 0

        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            if "public_platform_checkout:ip:" in key:
                self.ip_hits += 1
                if self.ip_hits > 2:
                    raise RateLimitExceeded(key=key, limit=limit, window=window)

    rl = _IpOnlyRl()

    async def _fake_dep():
        return rl

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        body = {
            "email": "rl_ip@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
        }
        assert (await client.post(CHECKOUT, json=body)).status_code == 200
        assert (await client.post(CHECKOUT, json=body)).status_code == 200
        r3 = await client.post(CHECKOUT, json=body)
        assert r3.status_code == 429
        err = r3.json()
        assert err.get("code") == "rate_limited"
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)


@pytest.mark.asyncio
async def test_public_platform_checkout_rate_limit_by_email(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    from src.main import app

    monkeypatch.setattr(settings, "yookassa_shop_id", "test-shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "test-secret")
    monkeypatch.setattr(settings, "rate_public_platform_checkout_ip_limit", 0)
    monkeypatch.setattr(settings, "rate_public_platform_checkout_email_limit", 1)
    monkeypatch.setattr(settings, "rate_public_platform_checkout_email_window_seconds", 600)
    from src.infrastructure.external_apis import yookassa_client as yk_mod

    _seq = 0

    def fake_create_platform_subscription_payment(self, *args, **kwargs):
        nonlocal _seq
        _seq += 1
        return f"prov-pay-em-{_seq}", "https://pay.example/yk"

    monkeypatch.setattr(
        yk_mod.YooKassaClient,
        "create_platform_subscription_payment",
        fake_create_platform_subscription_payment,
    )

    class _EmailRl:
        def __init__(self) -> None:
            self.by_key: dict[str, int] = {}

        async def check_or_raise(self, key: str, limit: int, window: int) -> None:
            if "email:" not in key:
                return
            self.by_key[key] = self.by_key.get(key, 0) + 1
            if self.by_key[key] > limit:
                raise RateLimitExceeded(key=key, limit=limit, window=window)

    rl = _EmailRl()

    async def _fake_dep():
        return rl

    app.dependency_overrides[get_rate_limiter] = _fake_dep
    try:
        body = {
            "email": "same@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
        }
        assert (await client.post(CHECKOUT, json=body)).status_code == 200
        r2 = await client.post(CHECKOUT, json=body)
        assert r2.status_code == 429
        assert r2.json().get("code") == "rate_limited"
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)


@pytest.mark.asyncio
async def test_public_platform_checkout_requires_turnstile_when_enabled(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """PRC-C1: with Turnstile on, every checkout must pass token verification (not only after soft IP)."""
    monkeypatch.setattr(settings, "yookassa_shop_id", "test-shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "test-secret")
    monkeypatch.setattr(settings, "turnstile_enabled", True)
    monkeypatch.setattr(settings, "turnstile_site_key", "site-key-test")
    monkeypatch.setattr(settings, "turnstile_secret_key", "secret-test")
    from src.infrastructure.external_apis import yookassa_client as yk_mod

    _cap_pay_seq = 0

    def fake_create_platform_subscription_payment(self, *args, **kwargs):
        nonlocal _cap_pay_seq
        _cap_pay_seq += 1
        return f"prov-pay-cap-{_cap_pay_seq}", "https://pay.example/yk"

    monkeypatch.setattr(
        yk_mod.YooKassaClient,
        "create_platform_subscription_payment",
        fake_create_platform_subscription_payment,
    )

    async def _verify_turnstile(token, *, remote_ip):
        from src.application.services.turnstile_service import TurnstileVerifyResult

        if token and str(token).strip():
            return TurnstileVerifyResult(ok=True, error_codes=[])
        return TurnstileVerifyResult(ok=False, error_codes=["missing-input-response"])

    monkeypatch.setattr("src.api.v1.routers.public_platform_signup.verify_turnstile", _verify_turnstile)

    body = {
        "email": "cap@example.com",
        "plan_slug": "start",
        "billing_period": "monthly",
    }
    r1 = await client.post(CHECKOUT, json=body)
    assert r1.status_code == 403
    j1 = r1.json()
    assert j1.get("code") == "captcha_required"
    assert (j1.get("details") or {}).get("site_key") == "site-key-test"

    r2 = await client.post(
        CHECKOUT,
        json={**body, "turnstile_token": "dummy-turnstile"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json().get("payment_url")


@pytest.mark.asyncio
async def test_public_platform_checkout_extra_modules_monthly_total(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    """Add-on list_price_rub is monthly; start + omni.embed.bundle → 2900 + 4900 (conftest seed)."""
    monkeypatch.setattr(settings, "yookassa_shop_id", "test-shop")
    monkeypatch.setattr(settings, "yookassa_secret_key", "test-secret")
    from src.infrastructure.external_apis import yookassa_client as yk_mod

    captured: dict[str, object] = {}

    def fake_create_platform_subscription_payment(self, *args, **kwargs):
        if args:
            captured["amount"] = args[0]
        else:
            captured["amount"] = kwargs.get("amount")
        return "prov-pay-extra", "https://pay.example/yk"

    monkeypatch.setattr(
        yk_mod.YooKassaClient,
        "create_platform_subscription_payment",
        fake_create_platform_subscription_payment,
    )

    r = await client.post(
        CHECKOUT,
        json={
            "email": "buyer-extra@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
            "extra_entitlement_keys": ["omni.embed.bundle"],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("payment_url") == "https://pay.example/yk"
    assert abs(float(str(data.get("amount_rub", 0))) - 7800.0) < 0.01
    assert captured.get("amount") is not None


@pytest.mark.asyncio
async def test_public_platform_checkout_extra_overlaps_plan_rejected(client: AsyncClient):
    """tasks.kanban is already in start — must not be passed as extra."""
    r = await client.post(
        CHECKOUT,
        json={
            "email": "overlap@example.com",
            "plan_slug": "start",
            "billing_period": "monthly",
            "extra_entitlement_keys": ["tasks.kanban"],
        },
    )
    assert r.status_code == 400
    assert r.json().get("code") == "extra_entitlement_overlaps_plan"
