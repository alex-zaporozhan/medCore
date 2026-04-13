# ADR-015: HTTP semantics when YooKassa verification fails on money webhooks

**Статус:** Accepted (2026-04-11)  
**Контекст:** QA_ARCH P0-3 / `BACKEND_AUDIT_TECH_LEAD_PRINCIPLE_2026-04-11.md` (вебхук не должен отдавать финальный 2xx, если состояние у провайдера не подтверждено).

## Решение

- **Контур A** (`POST /api/v1/payments/webhook`): если строка `payments` найдена по `object.id`, но `YooKassaClient.get_payment` бросает `YooKassaClientError`, обработчик отвечает **502** с телом `code: provider_verify_failed`. Локальное состояние брони/платежа не меняется. PSP может безопасно повторить уведомление.
- **Контур B** (`POST /api/v1/platform/billing/webhooks/yookassa`): та же логика для известной пары `platform_subscription_payments` + intent — **502** + тот же `code`, транзакция откатывается без перехода в `paid`/provision.

**Не меняется:** неизвестный `object.id` по-прежнему **200** + метрика `unknown_payment` (идемпотентно для «шума» провайдера).

## Последствия

- Метрики: `payment_webhook_failures_total{reason="provider_unavailable"}`, `platform_billing_webhook_total{result="provider_unavailable"}`.
- **503** на контуре B по-прежнему зарезервирован за «секрет вебхука не настроен» (`platform_webhook_not_configured`).

## Якоря в коде

- `src/application/webhook_provider_verify.py`
- `src/application/services/payment_service.py`, `src/api/v1/routers/payments.py`
- `src/application/services/platform_billing_service.py`, `src/api/v1/routers/platform_billing.py`
