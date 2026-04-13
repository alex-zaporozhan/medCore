# Публичный периметр: путь → защита → тест (PRC-C1 / WP1.3)

Матрица для регрессий и приёмки. Код ответа при срабатывании лимитера в API обычно **429** с `code: rate_limited` (нормализация в `main.py`).

| Поверхность | Механизм (app) | Тесты |
|-------------|----------------|--------|
| `POST /api/v1/public/platform/signup/checkout` | Redis fixed window: IP + email | `tests/api/test_public_platform_checkout.py`, `tests/api/test_public_platform_redis_rate_limit.py` |
| `GET /api/v1/public/platform/catalog/plans` (и родственные catalog GET) | IP | `tests/api/test_public_platform_catalog_rate_limit.py` |
| `POST /api/v1/platform/billing/webhooks/yookassa` | IP | `tests/api/test_platform_billing.py` (`test_platform_billing_webhook_rate_limit_*`) |
| `POST /api/v1/payments/webhook` | IP (контур A) | `tests/api/test_payments.py` (если есть сценарий лимита) |
| `GET/POST /api/v1/public/embed/v1/*` (health, session, webhook inbox, RAG) | IP (+ опционально token bucket для webhook) | `tests/api/test_phase1e_embed.py` (`test_public_embed_health_rate_limited_by_ip`, …) |
| Patient auth: неизвестный `clinic_slug` | IP | Настройки `RATE_AUTH_UNKNOWN_CLINIC_SLUG_*`; метрика `patient_auth_clinic_context_total` |
| Admin login | IP + email | `tests/api/test_admin_auth.py` или аналог |

**Edge/WAF** не дублируются в pytest; фиксируются в OPS ([10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](../architecture/arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md), nginx README для B).

**Версия:** 2026-04-08
