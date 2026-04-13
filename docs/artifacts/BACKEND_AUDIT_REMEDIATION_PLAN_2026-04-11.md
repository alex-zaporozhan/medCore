# План устранения замечаний BACKEND_AUDIT (2026-04-11)

**Источник:** `docs/artifacts/BACKEND_AUDIT_TECH_LEAD_PRINCIPLE_2026-04-11.md`  
**Роли планирования:** @ARCH (инварианты БД, границы транзакций, идемпотентность), @DEV (минимальный дифф, тесты, стиль репозитория).  
**Принцип:** одна фаза — один смысловой риск; миграции данных отдельно от «поведения API».

---

## Оси контроля

| Ось | Что проверяем |
|-----|----------------|
| **Данные / DDL** | Частичные уникальные индексы, FK, миграции без «немых» downgrade при невозможности отката |
| **Домен** | Единый источник правды для «слот занят / свободен», state machine бронирования |
| **API / HTTP** | Коды 4xx/5xx предсказуемы, вебхуки не 2xx при невосстановимой верификации провайдера |
| **Async / I/O** | Нет sync HTTP в event loop для горячих путей |
| **Надёжность** | Outbox, Celery, Redis — явные failure-режимы и метрики |
| **Наблюдаемость** | Метрики с низкой кардинальностью, алерты на silent path |

---

## Фазы (порядок исполнения)

### Фаза 1 — P0-1: слот врача после отмены (DONE в коде после merge этого блока)

- **ARCH:** частичный уникальный индекс PostgreSQL только для строк, которые **удерживают** слот (`deleted_at IS NULL` и статус не в множестве «отмена»).
- **DEV:** константа политики в `src/domain/booking_slot_policy.py`; `_ensure_slot_available` использует ту же семантику; `IntegrityError` при вставке → `BOOKING_SLOT_ALREADY_BOOKED`; тест API «создать → отменить → снова на тот же слот».
- **Риск отката миграции:** при downgrade повторное создание глобального `UNIQUE` упадёт, если в БД уже две строки с одним слотом (активная + отменённая). Downgrade оставить с комментарием или `batch`-очистка — по политике релиза.

### Фаза 2 — P0-2: YooKassa без блокировки event loop (DONE)

- `PaymentService.create_payment` / `handle_webhook`: `asyncio.to_thread` вокруг sync `create_payment` / `get_payment`.
- `platform_billing_service`: `get_payment` и `create_platform_subscription_payment` через `asyncio.to_thread`.
- Тесты, мокающие YooKassa на классе, должны принимать `*args` (вызов из worker thread позиционно).
- Единая точка входа для contour A/B при желании — отдельный async-обёртка-класс позже; сейчас точечно в сервисах.

### Фаза 3 — P0-3: вебхуки денег и верификация провайдера (DONE)

- Контракт: при ошибке `get_payment` для **известной** локальной строки оплаты — **502** + `provider_verify_failed`, без изменения статусов; PSP повторяет вебхук. Метрики: `payment_webhook_failures_total{reason="provider_unavailable"}`, `platform_billing_webhook_total{result="provider_unavailable"}`.
- ADR: [ADR-015-webhook-provider-verify-http-semantics.md](../adr/ADR-015-webhook-provider-verify-http-semantics.md).

### Фаза 4 — P1-1 / P1-4 / P1-5 (можно частично параллельно после фазы 3)

- P1-1 (**DONE**): вместо строки `bookings` по пустому слоту — **`pg_advisory_xact_lock`** по паре int32 от `(doctor_id, date, time)` (`src/application/booking_slot_advisory_lock.py` + `doctor_slot_advisory_lock_int32_pair` в `booking_slot_policy.py`) до `_ensure_slot_available` + insert/update; при переносе — два ключа в **детерминированном** порядке (антидедлок). `IntegrityError` → `BOOKING_SLOT_ALREADY_BOOKED` только если в сообщении есть `ux_bookings_doctor_slot_active` / `ux_bookings_doctor_slot`, иначе проброс. CSV импорт слота: lock + повторная проверка перед insert. **Сделано (2026):** расширение «освобождает слот» — `completed`, `no_show` в `BOOKING_STATUSES_RELEASE_DOCTOR_SLOT` + миграция `20260431_slot_release_outcomes`. **Бэклог:** любые дальнейшие статусы (например `draft` / `error`) — только в lockstep с миграцией индекса.
- P1-4 (**DONE в коде для контуров A + B checkout**): перед вызовом YooKassa создаётся локальная строка оплаты (`local-pending:{uuid}` → обновление на `provider_payment_id` провайдера). Contour B: `PlatformSubscriptionPayment` до `create_platform_subscription_payment`, `Idempotence-Key` = id строки; при ошибке создания — удаление заготовки. Contour A: `Booking` `FOR UPDATE`, затем `Payment` с префиксом `local-pending:`, идемпотентный повтор `create_payment` для той же брони с уже известным `provider_payment_id` — только `get_payment` + `confirmation_url` (без второго create в YooKassa). **Частично закрыто ops:** Celery-сверка зависших **`local-pending` в БД** (см. `payment_local_pending_reconcile_service`). **Остаётся бэклогом:** платёж есть у YooKassa, **локальной строки нет** — без list API / ops не автоматизировано; блокирующий 2PC не вводился.
- P1-5 (**частично DONE**): `send_with_fallback` возвращает третий признак доставки (`channel` | `log_only` | `failed`); Celery-уведомления и loyalty expiring-package пишут в `notifications.status` значение **`skipped_no_channel`** вместо ложного `sent` при log-only; recall-кампания — `RecallLog.skipped_no_channel` + счётчик `skipped_no_channel` в ответе `POST .../recall/campaigns/{id}/run`.

### Фаза 5 — P2 «инфра и периметр» (**DONE**)

- Async Redis — **пул на каждый event loop** (`redis_client.py`), закрытие всех пулов на shutdown.
- Rate limiter fail-open — счётчик `rate_limiter_redis_fail_open_total` + лог; карта метрик — `docs/architecture/07_metrics_observability.md`, операторский контур — `documentation/OBSERVABILITY.md`.
- Celery — `task_time_limit` / `task_soft_time_limit`, `broker_connection_retry_on_startup`, **`task_acks_late`**, **`task_reject_on_worker_lost`**, **`worker_prefetch_multiplier`**, **`worker_cancel_long_running_tasks_on_connection_loss`** из Settings; валидация **soft < hard** в `Settings`; `.env.example` — комментарии и рекомендуемая связка для прода (`ACKS_LATE` + `PREFETCH=1`).
- **Runbook + JWT:** `documentation/OBSERVABILITY.md` — разделы **Celery** и **JWT** (legacy dual-read, founder secret).

### Фаза 6 — Раздел 8 аудита (omnichannel / ERP / импорт) (**частично DONE**)

- **DONE (omni §8.1–8.3):** исходящий диспетчер пишет в `source_metadata` **`FAILED` / `SKIPPED` / `NOTIFIED_WAITER`** (WEB_WIDGET больше не `DELIVERED`), счётчик **`omni_outbound_dispatch_failed_total{reason}`**; Redis publish для admin SSE — **`omni_realtime_publish_failed_total{event}`** + алерты в `deploy/prometheus/dental_booking_alerts.yml`; операторский текст — `documentation/OBSERVABILITY.md`.
- **DONE (код):** webchat **Redis fan-out** (`WEBCHAT_REDIS_FANOUT_ENABLED`) — PUBLISH + long-poll SUBSCRIBE и выборка OUTBOUND `WEB_WIDGET` из БД после wake; ops «один воркер» остаётся допустимым режимом без Redis.
- **DONE (импорт §8.5):** CSV расписания — **построчная** обработка как у commerce (ошибки по строкам, статус job `completed_with_errors`, без отката уже принятых строк); docstring `CsvImportService.import_schedule_from_csv` обновлён под этот контракт.
- **DONE (код):** ERP nightly SLO-сигнал — `erp_aggregate_nightly_run_total` + алерт `ERP_NightlyRunPartialFailures`; построчный CSV расписания (ошибки по строкам, статус `completed_with_errors`) как у commerce.

---

## Трассировка к пунктам аудита

| ID аудита | Фаза |
|-----------|------|
| P0-1 | 1 |
| P0-2 | 2 |
| P0-3 | 3 |
| P1-1 | 4 (advisory lock + узкий IntegrityError; partial unique из фазы 1) |
| P1-2 | бэклог: уточнение enum / прочие статусы вне cancel+outcome — только с миграцией индекса (частично пересекается с закрытым расширением `no_show`/`completed`) |
| P1-3 | **частично в коде:** `kms_data_key.py` + `AWS_KMS_KEY_ID`; полная KMS-миграция секретов — отдельный эпик |
| P1-4, P1-5 | 4 |
| P2 3.1–3.17, 8.x | 5–6 по приоритету продукта |

---

## Статус

| Фаза | Статус |
|------|--------|
| 1 | Реализовано в репозитории (миграция + код + тест) |
| 2 | Реализовано: `asyncio.to_thread` для YooKassa в contour A + B checkout/webhook |
| 3 | Реализовано: 502 при сбое верификации YooKassa для известной оплаты (контуры A + B), ADR-015 |
| 4 | P1-1 (advisory lock + узкий IntegrityError) + P1-4 (A+B checkout) + часть P1-5; P1-4 reconciliation — **реализовано** (Celery + метрики) |
| 5 | Реализовано: Redis per-loop, fail-open метрика, Celery limits + acks/prefetch/cancel + runbook/JWT в OBSERVABILITY |
| 6 | Omni доставка/метрики/SSE; webchat Redis fan-out; CSV расписания построчно; ERP nightly run metric + алерт |

---

## QA_ARCH — проверка качества выполнения (2026-04-13)

Оценка: закрыты пункты бэклога из раздела «Очередь» предыдущей версии плана; часть решений — **MVP по риску** (идемпотентность и метрики есть, покрытие тестами и операторская документация усилены в этом проходе).

### Критические / высокие риски

| Риск | Вердикт | Действие |
|------|-----------|----------|
| **Webchat Redis: дубликаты на каждом long-poll по таймауту** | Был дефект реализации: при таймауте возвращалась выборка из БД за окно ~15s → виджет получал бы повторы на каждом ожидании. | **Исправлено:** при таймауте без Redis-сообщения возвращается пустой список; тест `tests/core/test_webchat_poll_redis_fanout.py`. |
| **Расхождение partial unique vs политика слота** | Регресс при правке только Python или только DDL. | Закрыто парой «код + миграция» + тест `tests/core/test_booking_slot_policy_predicate.py`. |
| **Reconcile платежей без идемпотентности** | Нарушение при повторных вызовах YooKassa. | Используются существующие ключи идемпотентности (A: booking_id, B: id строки оплаты). |

### Средние риски / «формально сделано»

| Тема | Замечание |
|------|-----------|
| **P1-4 ops: нет строки в БД, платёж только у YooKassa** | Реализована сверка для строк **`local-pending:*` в БД**; сценарий «commit не дошёл и строки нет» без list/search Payments API **не автоматизирован** — остаётся ops / ручной поиск по кабинету YooKassa или будущий эпик. |
| **P1-3 KMS** | Модуль и env — **фундамент**, не сквозное шифрование: Fernet и пути секретов клиники **не переведены** на KMS — ожидаемо по формулировке «отдельный эпик». |
| **Тесты reconcile** | Нет интеграционного теста с моком YooKassa на полный цикл Celery — **средний** техдолг; есть точечные тесты политики слота и webchat. |
| **`erp_aggregate_nightly_run_total` при 0 клиник** | Счётчик всё равно инкрементится с `success` — шум метрик в пустой БД; приемлемо для prod с данными. |

### Что можно улучшить (бэклог после QA)

- Webchat: опциональный **`Last-Event-ID` / курсор** в query long-poll, чтобы после wake отдавать только новые `message_id` без окна по времени.
- Reconcile: метка **`reconcile_attempts`** на строке оплаты или отдельная таблица аудита попыток (сейчас только Prometheus counter).
- CSV job: явное поле **`failed_row_count`** в API ответе (сейчас агрегат через `error` + `processed_rows`).
- Дашборд Grafana для `payment_local_pending_reconcile_total` и `erp_aggregate_nightly_run_total` (алерты есть, панели — по желанию OPS).

### Усиление в рамках этого ревью (выполнено)

- Исправление таймаута webchat Redis + unit-тест.
- Синхронизация **`documentation/OBSERVABILITY.md`** с новыми метриками/задачами/переменными (webchat, reconcile, ERP nightly).
- Приведение текста плана (фазы 4 и 6) в соответствие с фактическим кодом.

---

## Реестр: что выполнено в коде (детализация для аудита)

| ID плана / тема | Артефакты в репозитории |
|-----------------|-------------------------|
| P1-1 расширение статусов слота | `src/domain/booking_slot_policy.py`; Alembic `alembic/versions/20260431_booking_slot_release_no_show_completed.py`; тесты `tests/core/test_booking_slot_policy_predicate.py` (+ существующий `test_booking_slot_policy_lock.py`). |
| P1-4 ops reconcile | `src/application/services/payment_local_pending_reconcile_service.py`; `src/infrastructure/messaging/tasks/payment_reconciliation_tasks.py`; `src/infrastructure/messaging/celery_app.py` (include + beat); `src/core/config.py` (`payment_local_pending_reconcile_*`); `src/core/metrics.py` (`payment_local_pending_reconcile_total`); `deploy/prometheus/dental_booking_alerts.yml` (`PaymentLocalPendingReconcileErrors`). |
| Фаза 6 webchat | `src/application/services/webchat_push_manager.py` (`notify_webchat_outbound_wake`, `wait_for_webchat_poll_items`); `src/application/services/omnichannel_outbound_dispatcher.py` (порядок flush → wake, `delivery_semantics`); `src/api/v1/routers/integrations_gateway.py`; метрика `webchat_redis_fanout_total`; алерт `WebchatRedisFanoutPublishErrors`; тест `tests/core/test_webchat_poll_redis_fanout.py`. |
| CSV расписания построчно | `src/application/services/csv_import_service.py` (статусы `completed` / `completed_with_errors` / `failed`, лимит строк ошибок). |
| ERP nightly SLO-сигнал | `src/application/services/erp_aggregate_service.py` (`erp_aggregate_nightly_run_total`); `src/core/metrics.py`; алерт `ERP_NightlyRunPartialFailures` в `dental_booking_alerts.yml`. |
| P1-3 задел KMS | `src/infrastructure/security/kms_data_key.py`; `src/core/config.py` (`aws_kms_key_id`); `.env.example` (`AWS_KMS_KEY_ID`). |
| Документация и реестр метрик | `documentation/OBSERVABILITY.md`; `docs/artifacts/METRICS_REGISTRY.md` (M-R1…M-R3). |
| Пример конфигурации | `.env.example` (блоки reconcile, webchat, KMS, комментарий к ERP nightly metric). |

---

## Очередь / оставшийся бэклог (после закрытия строк 1–4)

1. **Частично** — P1-3: перевод чувствительных полей на KMS envelope + ротация + политика ключей (не только `generate_data_key`).
2. **Открыто** — сироты YooKassa без локальной строки оплаты (нет автоматического поиска по metadata без API провайдера / ops).
3. **Улучшения** — см. подраздел «Что можно улучшить» в отчёте QA_ARCH выше.

После каждой фазы: `poetry run pytest` по затронутым модулям + при необходимости полный suite перед релизом (Jenkins). Рекомендуемый минимум после изменений этого блока: `tests/core/test_booking_slot_policy_*.py`, `tests/core/test_webchat_poll_redis_fanout.py`, `tests/deploy/test_prometheus_alert_rules_yaml.py`, затронутые API-тесты omni/payments по регрессу.
