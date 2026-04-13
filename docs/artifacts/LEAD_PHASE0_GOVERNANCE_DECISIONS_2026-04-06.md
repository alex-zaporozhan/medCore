# LEAD — Phase 0 governance (решение победитель)

**Дата:** 2026-04-06. **Роль:** фиксация политики для закрытия долга Phase 0 (0-Q1…0-Q3, 0-F2, 0-F3) без переноса на чисто OPS-задачи. **Связь:** [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (Фаза 0), [STREAM_PHASE0_AND_GOVERNANCE.md](../architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md).

---

## §0-Q1 Контур A — shared secret в production

**Решение:** Сохраняем **мягкий дефолт** для совместимости MVP: при пустом `PATIENT_PAYMENT_WEBHOOK_SECRET` API стартует; в production пишется предупреждение в лог, если настроен YooKassa.

**Жёсткий fail-fast** включается явно: `ENFORCE_PATIENT_PAYMENT_WEBHOOK_SECRET_IN_PRODUCTION=true`. Тогда в `production` при пустом секрете приложение **не** поднимается (`RuntimeError` на старте). SEC waiver при отключённом секрете — только осознанный выбор с записью в тикете/релиз-нотах.

**Код:** `assert_enforced_patient_payment_webhook_secret_in_production()` в [`src/core/payment_webhook_governance.py`](../../src/core/payment_webhook_governance.py), вызов из [`src/main.py`](../../src/main.py) `lifespan`.

---

## §0-Q2 Per-IP rate limit для `POST /api/v1/payments/webhook`

**Решение:** Симметрия с контуром B — Redis fixed-window по IP, ключ `rate:patient_payment_webhook:ip:{ip}`. Настройки: `RATE_PATIENT_PAYMENT_WEBHOOK_IP_LIMIT`, `RATE_PATIENT_PAYMENT_WEBHOOK_IP_WINDOW_SECONDS`; при `TESTING=1` лимит принудительно 0 (как для других публичных лимитов). Ответ **429**, `code`: `rate_limited`, метрика `payment_webhook_failures_total{reason="rate_limited"}`.

**Код:** [`src/api/v1/routers/payments.py`](../../src/api/v1/routers/payments.py).

---

## §0-Q3 Алерт по `invalid_secret` (burst)

**Решение:** В [dental_booking_alerts.yml](../../deploy/prometheus/dental_booking_alerts.yml) добавлен **`PatientPaymentWebhookInvalidSecretBurst`** по `payment_webhook_failures_total{reason="invalid_secret"}`. Правило **`PaymentWebhookFailures`** уточнено по смыслу и `reason` (включая `rate_limited`).

---

## §0-F2 Crash-review МП + TARGET + RUBRIC

**Решение (победитель по скорости):** Полный построчный crash-review всего [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) **не** является воротом для данного среза. Инженерный минимум Phase 0:

- автоматизация: `scripts/phase0_governance_preflight.py` (`crash-review` / `all`);
- сводка процесса Phase 0: [STREAM_PHASE0_AND_GOVERNANCE.md](../architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md), [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (**0-F***).

Текстовая фиксация LEAD: корпус МП остаётся источником истины; расхождения «план ↔ код ↔ индексы» ведём через [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) и таблицу **§2b** в [ENTERPRISE_SAAS_TARGET.md](../architecture/ENTERPRISE_SAAS_TARGET.md). При обнаружении **критического** противоречия (безопасность, деньги, изоляция данных) — отдельный эпик ARCH без ожидания «полного» crash-review.

---

## §0-F3 Синхронизация INDEX / TARGET / RUBRIC (§2b)

Полная таблица выравнивания и дата фиксации — в [ENTERPRISE_SAAS_TARGET.md](../architecture/ENTERPRISE_SAAS_TARGET.md) раздел **«§2b Выравнивание якорей»**.
