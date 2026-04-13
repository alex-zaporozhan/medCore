# SLO и бюджет ошибок: критичные пути (LEAD)

> **Статус:** целевые ориентиры; не SLA договора до отдельного решения.  
> **Связь:** [07_metrics_observability.md](../architecture/07_metrics_observability.md), [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md).

**Cardinality (QA_ARCH):** цели ниже относятся к **низкокардинальным** сериям; не подмешивать `organization_id` в лейблы алертов по умолчанию — [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M1. Проверка на staging при Фазе **1d** — §15b мастер-плана.

## 1. Публичные пути

| Путь | Доступность (ориентир) | p95 latency (ориентир) |
|------|------------------------|-------------------------|
| `GET /health` | 99.5% / 30 дней | меньше 200 ms |
| `POST /api/v1/payments/webhook` | 99% без 5xx | меньше 3 s |
| auth send-code / verify-code | 99% | меньше 2 s |

## 2. Запись и оплата

| Путь | Ориентир |
|------|----------|
| Бронь + создание платежа | p95 меньше 5 s |
| Доля 5xx booking/payment | меньше 0.5% за 7 дней |

## 3. Бюджет ошибок

- Рост `payment_webhook_failures_total` — расследование за одну смену при удвоении к среднему за 7 дней.
- Потеря денег / двойное списание — вне бюджета, немедленный rollback.

## 4. Контур B (подписка платформы, PRC-G2)

| Путь / сигнал | Ориентир |
|---------------|----------|
| `POST /api/v1/platform/billing/webhooks/yookassa` | 99% без 5xx (после валидного секрета); p95 меньше 5 s |
| `POST /api/v1/public/platform/signup/checkout` | 99% без 5xx; p95 меньше 5 s |
| `platform_billing_webhook_total{result=processing_error}` | расследование при устойчивом росте — см. алерты в `dental_booking_alerts.yml` |
| `platform_signup_intent_stuck` / DLQ | 0 в установившемся режиме дольше порога runbook — см. [PLATFORM_BILLING_PROVISION_RECONCILE.md](./PLATFORM_BILLING_PROVISION_RECONCILE.md) и [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) §10 |
| Outbox (`domain_outbox_oldest_pending_age_seconds`) | см. **DomainOutboxOldestPendingStale** (PRC-E3) |

Тюнинг порогов Prometheus — после калибровки на staging; связка с дашбордом **Platform SaaS — contour B** (`dental_booking_observability_w1_w2.json`).

**Версия:** 2026-04-08 (contour B: ссылка на reconcile runbook)
