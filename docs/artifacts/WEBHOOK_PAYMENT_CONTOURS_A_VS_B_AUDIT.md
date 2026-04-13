# Аудит платёжных webhook: контур A (пациент→клиника) vs B (подписка платформы)

> **Назначение:** зафиксировать факт разведения путей и секретов в репозитории (Фаза 0, [01_PHASE_0_PREPARATION.md](../architecture/arch_plan/01_PHASE_0_PREPARATION.md)).  
> **Мастер-план:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §6, §2c (U-006 / C1).

## Контур A — оплата записи / пациент → клиника

| Элемент | Значение |
|---------|----------|
| Обработчик | `PaymentService.handle_webhook`, роутер пациентских/клинических платежей (см. `payments` router и интеграции) |
| Провайдер | YooKassa per-clinic или глобальные креды клиники |
| Секрет | **Не** `PLATFORM_BILLING_WEBHOOK_SECRET`; верификация через привязку `provider_payment_id` к строке `Payment` и вызов API YooKassa |
| Идемпотентность | По записям платежей бронирования, статусы `succeeded` / отмена — см. `payment_service` |

## Контур B — подписка SaaS (Владелец → платформа)

| Элемент | Значение |
|---------|----------|
| HTTP | `POST /api/v1/platform/billing/webhooks/{provider}` (`provider=yookassa`) |
| Код | `src/api/v1/routers/platform_billing.py`, `src/application/services/platform_billing_service.py` |
| Заголовок секрета | `X-Platform-Billing-Webhook-Secret` |
| Конфиг | `PLATFORM_BILLING_WEBHOOK_SECRET` (`.env.example`) |
| Данные | `platform_signup_intents`, `platform_subscription_payments`; провижининг org + clinic + entitlements + владелец (Фаза 1b) |

## Вывод

Контуры **разведены по URL и секрету B**; пациентский поток **не** использует заголовок платформенного webhook. Приёмка DoD **§15b 1b** требует ещё OpenAPI B, расширенные ветки тестов и полный жизненный цикл §16.6 — см. [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md).

**Проверка в коде (grep):** `platform/billing/webhooks`, `PLATFORM_BILLING_WEBHOOK_SECRET`, `handle_platform_billing_yookassa_webhook`, `handle_webhook` в `payment_service`.
