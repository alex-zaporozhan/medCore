"""P0-3 / QA_ARCH: PSP must not receive final 2xx when YooKassa verification failed for a known local payment row."""


class PaymentWebhookProviderVerifyError(Exception):
    """Contour A: `payments` row matched `object.id` but YooKassa ``get_payment`` failed."""

    pass


class PlatformBillingWebhookProviderVerifyError(Exception):
    """Contour B: `platform_subscription_payments` row matched but YooKassa ``get_payment`` failed."""

    pass
