# Edge hardening: platform billing webhook B (1b-E6 / 10-Q4)

Публичный путь: `POST /api/v1/platform/billing/webhooks/yookassa` (префикс API зависит от `API_V1_PREFIX`).

## Уже в приложении

- Заголовок `X-Platform-Billing-Webhook-Secret` (см. OpenAPI / `platform_billing.py`).
- Per-IP rate limit через Redis (`RATE_PLATFORM_BILLING_WEBHOOK_IP_LIMIT`, `RATE_PLATFORM_BILLING_WEBHOOK_IP_WINDOW_SECONDS`).

## Рекомендация на nginx (пример)

Отдельный `location` с более жёстким лимитом, чем общий API, и при необходимости allowlist IP YooKassa (актуальный список — в документации провайдера):

```nginx
# Пример: префикс /api/v1 как в дефолтном приложении
limit_req_zone $binary_remote_addr zone=platform_billing_wh:10m rate=30r/m;

location = /api/v1/platform/billing/webhooks/yookassa {
    limit_req zone=platform_billing_wh burst=10 nodelay;
    limit_req_status 429;
    proxy_pass http://backend_upstream;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Подбирайте `rate` согласованно с лимитом в приложении и с политикой провайдера. WAF (Cloudflare, AWS WAF и т.д.) — дополнительно к nginx.

## Ссылки

- Модуль: `docs/architecture/modules/platform_subscription_billing.md` §6–§7, §10.
- Сквозной трек: `docs/architecture/arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md` (10-Q4).
