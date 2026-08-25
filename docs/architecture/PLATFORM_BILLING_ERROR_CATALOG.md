# Каталог ошибок и сообщений: платежи и платформа (LEAD)

> **Назначение:** единый ориентир для API, UI Основателя и саппорта.  
> **Контур A** — пациент к клинике (`PaymentService`, `/api/v1/payments/webhook`). **Контур B** — подписка платформы (`platform_billing_service`, `POST /api/v1/platform/billing/webhooks/{provider}`, ADR-011).

**Глобальная форма JSON-ошибок и нормализация `code`:** [API_PUBLIC_ERROR_CODES.md](./API_PUBLIC_ERROR_CODES.md) (1c-Q2).

Коды — **стабильные** строки в **lowercase snake_case** в HTTP-ответе; тексты пользователю могут локализоваться.

## 1. Webhook и провайдер (контур A, текущий код)

| Код | HTTP | Когда | Действие |
|-----|------|-------|----------|
| `invalid_json` | 400 | Тело не JSON | Провайдер: повтор с корректным телом |
| `webhook_processing_failed` | 500 | Необработанное исключение | Логи, метрики `payment_webhook_failures_total` |

**Фоновые (HTTP 200):**

| Ситуация | Поведение |
|----------|-----------|
| Неизвестный `provider_payment_id` | warning в логах |
| Нет `id` в payload | warning в логах |
| Ошибка `get_payment` у YooKassa | exception в логах |

## 2. Webhook контура B (реализация в коде)

| Код | HTTP | Когда | Действие |
|-----|------|-------|----------|
| `platform_webhook_not_configured` | 503 | `PLATFORM_BILLING_WEBHOOK_SECRET` пуст в приложении | Настроить секрет OPS; не вызывать URL до конфигурации |
| `platform_webhook_invalid_signature` | 403 | Заголовок `X-Platform-Billing-Webhook-Secret` неверен или отсутствует | Провайдер: корректный секрет |
| `invalid_json` | 400 | Тело не JSON | Повтор с корректным телом |
| `webhook_processing_failed` | 500 | Необработанное исключение | Логи; метрика `platform_billing_webhook_total{result="processing_error"}` |

**Фоновые (HTTP 200, без смены состояния):**

| Ситуация | Поведение |
|----------|-----------|
| Неизвестный `provider_payment_id` (нет строки в `platform_subscription_payments`) | warning в логах; метрика `unknown_payment` |
| Нет `id` в payload | warning; метрика `missing_payment_id` |
| Повторный `succeeded` для уже активированного intent | идемпотентно; метрика `idempotent_ok` |

**Целевые коды (UI reconcile / retry — по мере реализации):**

| Код | Сценарий |
|-----|----------|
| `platform_provision_failed` | Оплата ок, провижининг в retry |
| `platform_reconcile_idempotent` | Повтор reconcile без изменения |

## 3. UI Основателя: reconcile (C2)

| Состояние intent | Смысл |
|------------------|-------|
| `manual_review` | Нужно действие Основателя |
| `failed` | Алерт, кнопка повторить провижининг |
| `paid` без org | Висящая оплата (метрика ADR-011) |

## 4. Ответственность

- **DEV:** коды из таблицы; не плодить синонимы.
- **Product:** тексты UI.
- **LEAD:** новые публичные денежные пути.

**Версия:** 2026-08-24

## 5. Вход администратора клиники (ADR-012)

| Код | HTTP | Когда | UI |
|-----|------|-------|-----|
| `billing_revoked` | 403 | `POST /api/v1/admin/auth/login` и любой admin JWT, если у org отозвана подписка платформы | `errors.billing_revoked` |
| `invalid_credentials` | 401 | Неверный email/пароль (без различия «нет пользователя») | `errors.invalid_credentials` |
| `rate_limited` | 429 | Лимит попыток входа | `errors.rate_limited` |

`detail` канонически на английском; локаль — только в UI.
