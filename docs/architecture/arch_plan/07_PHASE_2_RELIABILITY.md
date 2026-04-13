# Фаза 2 — надёжность: BCP, outbox, CI (Phase_2_Reliability)

**Узлы МП mermaid:** `ADR008_BCP`, `ADR009_outbox`, `CI_U008`.  
**Связь МП:** §16.2–16.3, §17.1, §19 п.6–7, 11, U-007–009, [09_backup_restore_bcp.md](../09_backup_restore_bcp.md), [domains/booking_event_chain.md](../domains/booking_event_chain.md).

## Архитектурный целевой образ

1. **ADR-008** — проверяемые бэкапы, алерт «stale backup», drill отражён в [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md).
2. **ADR-009** — outbox (или эквивалент) для критичных цепочек; метрики lag; снятие риска «commit есть — событие потеряно» при N репликах (МП §17.1, §2b слой E).
3. **U-008** — CI не «отключён навсегда»; политика в воротах §19 п.7.
4. **Связка с биллингом B** — в ADR-011 / модуле явно: что синхронно в HTTP-транзакции, что через outbox/очередь (МП §19 п.11, C2).

## Порядок работ @DEV

1. Таблица outbox + продюсер/консьюмер; перевести выбранные домены (payment/booking — по ADR) с in-process bus на устойчивую доставку.
2. Метрики очереди/lag; алерты с `runbook_url`.
3. Интеграционные тесты: идемпотентность consumer, повторная доставка.
4. Совместно с @OPS: сценарии restore и доказательство drill (U-009).
5. **CI (связка с QA_ARCH / 1c):** по политике U-008 не оставлять только «узкий» pytest в долгую перспективу — расширить [`.github/workflows/build-and-test-entitlements.yml`](../../../.github/workflows/build-and-test-entitlements.yml) (или основной build/test workflow) на **`poetry run pytest tests/`** либо поэтапно по маркерам, когда стабильны runner и сервисы. Якорь: [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) B3, [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q3**, [08_tests_matrix.md](../08_tests_matrix.md).

## Зависимости

- **§17.1** — outbox часто является **выбранным** путём для публичного денежного контура при multi-replica.
- Не масштабировать API горизонтально без решения по этой связке (МП §17).

## DoD

- ADR-008/009 в статусе, соответствующем коду, или явный ADR риска с датой пересмотра.
- CI policy задокументирована; критичные ветки защищены.

## Ссылки

- [06_cache_redis_celery.md](../06_cache_redis_celery.md)
- [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md)

## Статус @DEV (2026-04-06; поток Phase 2 epics — 2026-04-13)

- **ADR-009 (частично):** таблица `domain_outbox`; **контур A:** `PaymentSuccess` + `get_session_payment_webhook`; **контур B:** `PlatformSignupProvision` после `paid` + немедленный `dispatch_domain_outbox_batch` в webhook; **booking:** `emit_booking_domain_event` + `get_session_booking_domain_outbox` на роутере `bookings`. Celery `domain_outbox.dispatch_pending` каждые 30s. Env: `DOMAIN_OUTBOX_*` (в т.ч. `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED`, `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED`). Метрики: перечисленные ранее + `domain_outbox_post_commit_dispatch_failures_total` (сбой drain после commit HTTP). Алерты: `DomainOutboxOldestPendingStale`, `DomainOutboxPendingBacklog`, `DomainOutboxBlockedByAttemptCap`, `DomainOutboxPostCommitDispatchFailures` — `deploy/prometheus/dental_booking_alerts.yml`.
- **ADR-008 (частично):** метрики логического экспорта клиники `backup_logical_export_*` в `backup_tasks`; алерт **info** `BackupLogicalExportSuccessStale` (заглушить в Alertmanager, если экспорт не планируется); [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) §8; кластерный backup — managed-DB/OPS вне API.
- **Связка ADR-011 / контур B:** §4.4 в [platform_subscription_billing.md](../modules/platform_subscription_billing.md) (синхрон vs outbox при multi-replica / §17.1).
- **1c-Q3 / U-008:** job **`full-backend-tests`** — `poetry run pytest tests/` **без** `continue-on-error` на PR и push (локально suite зелёный).
- **Бэклог сверх DoD:** единый список **2-F1…2-F8** — § «Бэклог после минимального DoD» ниже и [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).

### CI (1c-Q3 / U-008)

Workflow [`.github/workflows/build-and-test-entitlements.yml`](../../../.github/workflows/build-and-test-entitlements.yml): `verify` (узкий pytest + фронт) и **`full-backend-tests`** (`pytest tests/`).

## Приёмка QA_ARCH (2026-04-06)

- **Отчёт:** [STREAM_PHASE2_RELIABILITY_EPICS.md](./STREAM_PHASE2_RELIABILITY_EPICS.md), ADR-008/009 — риски, формальности, бэклог **2-F*** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).
- **Усиления в коде (тот же день):** throttle DB для gauge на `GET /metrics` (`DOMAIN_OUTBOX_METRICS_DB_REFRESH_MIN_INTERVAL_SECONDS`, в тестах `TESTING=1` → 0); счётчик `domain_outbox_gauge_refresh_failures_total`; опциональный cap `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS` + gauge `domain_outbox_blocked_by_attempt_cap_rows` + алерт `DomainOutboxBlockedByAttemptCap`; явная ошибка `corrupt_outbox_payload` при битом JSON payload; после dispatch — `refresh_domain_outbox_gauges(force=True)`.

## Приёмка QA_ARCH — поток STREAM Phase 2 epics (2026-04-13)

- **Отчёт:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**2-F***, **2-E1…E4**) — критичные/средние риски, формальности, хвосты.
- **Усиления в коде (тот же цикл):** post-commit `dispatch_domain_outbox_batch` обёрнут в try/except в `get_session_booking_domain_outbox` и `get_session_payment_webhook` (не роняем ответ после успешного commit; Celery подбирает очередь); метрика + алерт `DomainOutboxPostCommitDispatchFailures`.

## Бэклог после минимального DoD (что доделать позже — единый указатель)

Всё ниже имеет стабильные ID **2-F*** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (закрытие строки — только с PR/ADR/ticket).

| ID | Суть |
|----|------|
| **2-F1** | См. [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — ядро закрыто (booking outbox); хвост PATCH admin / статус. |
| **2-F2** | **U-009:** drill restore + RPO/RTO в §1 [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) — **partial**, хвост OPS. |
| **2-F3** | Dead-letter / tombstone для outbox — **open**. |
| **2-F4** | Кластерный backup managed-DB — **open** (OPS). |
| **2-F5** | Тесты redelivery / идемпотентность по типам — **partial**; см. backlog. |
| **2-F6** | ADR-008/009 = факт кода — **open** (добавить `domain_outbox_post_commit_*` в текст ADR или amendment). |
| **2-F7** | Контур B multi-replica — **partial** (outbox в коде; OPS ingress). |
| **2-F8** | CI e2e/security — **done** по политике LEAD; Trivy FS включён отдельно — см. [STREAM_PHASE2_RELIABILITY_EPICS.md](./STREAM_PHASE2_RELIABILITY_EPICS.md). |
