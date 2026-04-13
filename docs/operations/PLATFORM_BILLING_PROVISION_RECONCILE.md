# Runbook: провижининг контура B (signup → org) — stuck, DLQ, ручное закрытие

> **Связь:** [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) §7, §10, §12; PRC-B4, PRC-E3; алерты `PlatformSignupIntentProvisionBacklog`, `PlatformSignupIntentDeadLetter`, `DomainOutbox*`.

## Когда открывать

- Алерт **PlatformSignupIntentProvisionBacklog** (`platform_signup_intent_stuck` > 0 дольше порога).
- Алерт **PlatformSignupIntentDeadLetter** (`platform_signup_intent_dead_letter` > 0).
- Алерт **DomainOutboxOldestPendingStale** / **DomainOutboxPendingBacklog** (провижининг через outbox после `succeeded`).

## UI Основателя

- Страница **`/platform/provision-queue`** (JWT Основателя): список intent с `provision_last_error`, DLQ, **Retry** и **Закрыть вручную** (terminal reconcile без SQL).
- **Retry:** `POST /api/v1/platform/internal/signup-intents/{intent_id}/retry-provision` — идемпотентно; **не** обходит гейт каталога (409 при `amount_mismatch_catalog` и т.п.).
- **Закрыть вручную:** `POST /api/v1/platform/internal/signup-intents/{intent_id}/manual-close` с телом `{"note": "…"}` (опционально) — только для `provision_failed` / `dead_letter`; переводит intent в **`reconcile_closed_manual`**, снимает **`provision_dead_letter`** (чтобы `platform_signup_intent_dead_letter` не оставался завышенным), аудит `platform_signup_intent_manual_close` только при первом применении; повтор вызова для уже закрытого intent — **200 без дубля аудита** (метрика `platform_provision_manual_close_total{result="noop"}`). Использовать после внешнего разбора в YooKassa/поддержке, когда повторный провижининг нежелателен.

## Фоновые задачи (OPS)

- Celery **`platform_billing.retry_due_provisions`** — backoff для временных ошибок.
- Celery **`domain_outbox.dispatch_pending`** — доставка outbox после commit (ADR-009); при `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED=true` провижининг идёт через outbox.

## Chargeback / refund (ADR-012)

- Webhook B: при `status` платежа `refunded` или эквивалент chargeback/dispute (`chargeback`, `disputed`, … в коде) — отзыв entitlements и `suspended`; см. §12 модуля и тесты `tests/api/test_platform_billing.py`.

## Phase 3 — rollout entitlements (серверный гейт)

- Переменные: **`ENTITLEMENT_ENFORCEMENT_MODE`** (`legacy` | `auto` | `strict`), **`ENTITLEMENT_ENFORCEMENT_STRICT_ORG_IDS`** (CSV UUID для поэтапного strict в режиме `auto`). Подробнее: `src/application/services/organization_entitlement_access.py`, тесты `tests/application/test_organization_entitlement_access.py`.

**Версия:** 2026-04-08 (DEV: Phase 2/3 operational closure)
