# QA_ARCH: срез 1b-E3 — OpenAPI webhook B + матрица веток

**Дата:** 2026-04-06  
**Epic:** 1b-E3  
**Статус:** закрыт по минимальному DoD (расширение контракта + регрессионные тесты веток)

## OpenAPI

- `POST /api/v1/platform/billing/webhooks/{provider}` — расширены `openapi_examples` в `Body`: `payment.succeeded`, `payment.canceled`, `refund`-ориентированный пример (см. `platform_billing.py`).
- Стандартные ответы ошибок уже описаны в `PLATFORM_BILLING_WEBHOOK_OPENAPI`.

## Pytest (ветки / периметр)

- Существующая матрица в `tests/api/test_platform_billing.py` (succeeded, idempotent, canceled, refunded, tariff gate, rate limit, …).
- Добавлено: `test_platform_billing_webhook_unknown_provider_returns_404` (неизвестный `provider` в path).

## DoD

- [x] Дополнительные примеры тела уведомления в OpenAPI.
- [x] Pytest на ветку unknown provider; остальные ветки покрыты накопленными тестами файла.

## Остаточный долг

- Полный формальный контракт всех кодов YooKassa в отдельном YAML — по необходимости Product/SEC (**1b-F2**).
