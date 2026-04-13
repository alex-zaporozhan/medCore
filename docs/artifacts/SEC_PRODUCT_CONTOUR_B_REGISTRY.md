# Реестр SEC + Product — контур B (webhook подписки платформы)

**Роль:** согласование угроз и поведения между **SEC**, **Product** и **DEV**.  
**Связь:** [QA_REPORT_1b_E3b_webhook_contract.md](./QA_REPORT_1b_E3b_webhook_contract.md), [platform_yookassa_webhook_b_branches.yaml](../architecture/contracts/platform_yookassa_webhook_b_branches.yaml), [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) §12.1.

## Контроль доступа и доверие

| Тема | Решение (факт кода) | Владелец | Пересмотр |
|------|---------------------|----------|-----------|
| Аутентификация webhook | Заголовок `X-Platform-Billing-Webhook-Secret` (constant-time compare) | SEC | При смене провайдера |
| Секрет в проде | Не в git; ASM / Secret Manager — см. [PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md](../operations/PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md) | OPS + SEC | Ротация |
| Rate limit / edge | App Redis per-IP + `PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS`; edge — [README_PLATFORM_BILLING_WEBHOOK.md](../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md) | OPS | PRC-B7 |
| Идемпотентность провайдера | 200 на unknown `object.id` + метрика `unknown_payment` (без изменения БД посторонних платежей) | Product + SEC | Fraud review |

## Поведение денег и org (Product)

| Ветка | Продуктовое решение | Документ |
|-------|----------------------|----------|
| `succeeded` + гейт каталога | Не переводить в `paid` при расхождении суммы/плана | Модуль §4.3 |
| Retry основателя | Не обходить гейт без **1b-F6a** (override + audit) | PHASE_FULL_CLOSURE **1b-F6** |
| `refunded` | ADR-012: suspended + отзыв entitlements, org сохраняется | ADR-012 |

## Подпись приёмки

| Роль | Имя / дата | Комментарий |
|------|------------|-------------|
| **LEAD** | _дата / тикет_ | Периметр L3 |
| **SEC** | _дата_ | Публичный webhook B |
| **Product** | _дата_ | Матрица веток YAML |

**Версия:** 2026-04-06 (LEAD)
