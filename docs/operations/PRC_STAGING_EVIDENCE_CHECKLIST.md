# PRC: staging-доказательства (C1, B7, F1, F3, G2)

Чеклист для **staging** (или эквивалентного pre-prod), чтобы закрыть строки матрицы [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md), которые зависят от среды, а не только от кода в git.

Ответственный: **OPS + QA_ARCH** (по задаче); дата факта — в тикете.

## PRC-C1 — публичный периметр (signup/checkout, rate limit)

- [ ] Поднят API + Redis с теми же env-классами, что планируется в prod (лимиты **не** обнулены `TESTING=1`).
- [ ] `POST .../public/platform/signup/checkout`: превышение IP/email лимита → **429**, тело с `code=rate_limited` (см. тесты `tests/api/test_public_platform_checkout.py`, `test_public_platform_redis_rate_limit.py`).
- [ ] `GET .../public/platform/catalog/*`: IP лимит → 429 (см. `tests/api/test_public_platform_catalog_rate_limit.py`).
- [ ] Капча/Turnstile (если включена в конфиге): негативный сценарий зафиксирован в тикете или e2e.
- [ ] Ссылка на артефакт: скрин/лог HAR или ID прогона Playwright (если есть).

## PRC-B7 — webhook B + edge (WAF)

- [ ] App-layer: IP rate limit на `POST .../platform/billing/webhooks/yookassa` → 429 при burst (тесты `tests/api/test_platform_billing.py`).
- [ ] Edge/WAF: правило на пути webhook B зафиксировано в OPS ([deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md)) или тикет «не применимо» для текущего контура.
- [ ] Алерт `PlatformBillingWebhookRateLimitedBurst` проверен на тестовом firing (опционально через нагрузочный скрипт на staging).

## PRC-F1 — Grafana / непубличная сеть

- [ ] Grafana не доступна из интернета без VPN/auth (проверка OPS).
- [ ] [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md) пройден локально/staging.

## PRC-F3 — cardinality метрик

- [ ] Выборка `/metrics` на staging: для `platform_billing_*`, `spam_blocked_total`, `embed_public_request_total` нет сырых email/PII в labels (см. [07_metrics_observability.md](../architecture/07_metrics_observability.md) если есть).
- [ ] Зафиксирован вывод (фрагмент scrape или скрин Prometheus targets).

## PRC-G2 — SLO критичных путей

- [ ] Таблица в [SLO_CRITICAL_PATHS.md](./SLO_CRITICAL_PATHS.md) согласована с фактическими алертами в `deploy/prometheus/dental_booking_alerts.yml`.
- [ ] Хотя бы один «сухой» прогон: из правила с `runbook_url` перейти по ссылке и выполнить первый шаг runbook (без прод-данных).

## Связь с кодом

Матрица «путь → тест → защита»: [PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md](../review/PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md).

**Версия:** 2026-04-08
