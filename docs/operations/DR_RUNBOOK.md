# DR_RUNBOOK — восстановление и учения

> **Связь:** [ADR-008](../adr/ADR-008-backup-restore-bcp.md), [09_backup_restore_bcp.md](../architecture/09_backup_restore_bcp.md), [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (**2-F2** restore drill).  
> **Релиз:** общий чек-лист — [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md); целевые SLO — [SLO_CRITICAL_PATHS.md](./SLO_CRITICAL_PATHS.md).

## 1. Цели RPO / RTO (заполнить для среды)

Целевые значения и факт по **managed PostgreSQL / staging PITR** заполняет **OPS** после реального учения; до заполнения строки ниже остаются пустыми (это не отменяет учёт учений в п. 6.1).

| Метрика | Целевое значение | Факт последнего drill (дата) |
|---------|------------------|-------------------------------|
| RPO | Задать OPS для managed-DB (PITR — по SLA провайдера) | — |
| RTO | Задать OPS (восстановление сервиса после объявления инцидента) | — |
| **Учёт в репо (U-009)** | CI: [`.github/workflows/dr-restore-drill.yml`](../../.github/workflows/dr-restore-drill.yml) (`workflow_dispatch`) | **2026-04-06** — зафиксирован сценарий в репозитории; **квартальный** полноценный restore на **staging** и дата в этой таблице — ответственность **OPS** / on-call. |

## 2. Managed PostgreSQL (рекомендуемый прод)

1. Остановить трафик на приложение (maintenance page / scale API to 0).
2. Выполнить restore из консоли провайдера (point-in-time или снапшот) по инструкции провайдера.
3. Обновить `DATABASE_URL` при смене endpoint (если применимо).
4. Прогнать `alembic upgrade head` если версия образа опережает схему снапшота (или наоборот — по политике).
5. Smoke: `/health`, `/health/replica`, критичный read-only запрос.
6. Включить трафик; мониторинг error rate 30–60 мин.

**Владелец шагов:** OPS + DEV on-call.

## 3. Docker / on-prem (том `pgdata`)

1. Остановить `backend`, `celery`, `celery-beat`.
2. Сохранить текущий том или каталог данных как `pgdata.failed.<timestamp>`.
3. Восстановить из последнего проверенного `pg_dump` / snapshot тома по внутренней инструкции команды.
4. Поднять `db`, дождаться healthy.
5. Запустить `migrations`, затем приложение.
6. Smoke как в п. 2.

## 4. Redis / Celery после восстановления БД

- Очереди могут содержать устаревшие задачи: политика **purge** отдельных очередей или drain с осторожностью (ADR по replay).
- После restore проверить **стыки** Booking/Payment/ERP (см. трекер §10.1).

## 5. Tenant logical export (не полный DR)

Выполняется **приложением** по процедуре поддержки, не вместо кластерного backup. См. [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../architecture/TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).  
**Черновик процедуры offboarding + экспорта (SaaS §15b 1e):** [TENANT_OFFBOARDING_AND_EXPORT.md](./TENANT_OFFBOARDING_AND_EXPORT.md).  
**Доступ Основателя / break-glass (SaaS §19 п.18):** [FOUNDER_ACCESS_BREAKGLASS.md](./FOUNDER_ACCESS_BREAKGLASS.md).

## 6. Учение (drill)

Минимум: один успешный restore на **staging** в квартал; записать дату, длительность, отклонения от RTO/RPO. Повторяемость в CI: **Actions → DR restore drill** (`.github/workflows/dr-restore-drill.yml`, только `workflow_dispatch`, U-009).

### 6.1 Журнал учений (фиксировать здесь)

| Дата | Среда | Сценарий | RTO факт | RPO факт | Примечание |
|------|--------|----------|----------|----------|------------|
| 2026-04-06 | CI (GitHub Actions) | `workflow_dispatch` [dr-restore-drill.yml](../../.github/workflows/dr-restore-drill.yml) — проверка воспроизводимости job restore (синтетический сценарий) | — | — | Полный staging PITR и заполнение §1 — владелец OPS; связка U-009 |

## 7. Grafana и наблюдаемость (SaaS §11 M5)

Grafana и Prometheus не должны быть доступны из публичной сети без аутентификации и сетевого периметра (VPN / SSO / BasicAuth за reverse-proxy). Матрица, кто видит тенантные срезы — только Основатель и доверенный OPS; см. [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M5 и [deploy/grafana/README.md](../../deploy/grafana/README.md).

## 8. BCP: кластер vs приложение (Phase 2 / ADR-008)

| Сигнал | Смысл |
|--------|--------|
| **Managed PostgreSQL** (снапшоты, PITR) | Основной **кластерный** backup; просрочку снимает провайдер или внешний экспортёр — не дублируется в коде API. |
| `backup_logical_export_*` | Успешные **логические** JSON-экспорты по клинике через Celery `backup_tasks.run_full_backup` — *не* замена кластеру. Алерт `BackupLogicalExportSuccessStale` в [dental_booking_alerts.yml](../../deploy/prometheus/dental_booking_alerts.yml) — **info**, при отсутствии расписания экспорта заглушить в Alertmanager. |
| `domain_outbox_*` | Очередь ADR-009: контур A `PaymentSuccess`, контур B `PlatformSignupProvision`, события booking — застой — см. [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md). |
| `domain_outbox_post_commit_dispatch_failures_total` | Сбой `dispatch_domain_outbox_batch` после успешного commit HTTP (booking/payment webhook); строки остаются для Celery; алерт `DomainOutboxPostCommitDispatchFailures`. |
| `domain_outbox_blocked_by_attempt_cap_rows` | При `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS > 0`: строки с `attempts >= cap` не диспатчатся; смотреть `last_error`, вручную исправить payload или удалить строку после расследования. Алерт `DomainOutboxBlockedByAttemptCap`. |
| `domain_outbox_gauge_refresh_failures_total` | Ошибки БД при обновлении gauge на `GET /metrics` — проверить пул соединений и доступность primary. |

Учение **U-009:** квартальный restore на staging — п. 6; фиксировать дату и отклонения от RPO/RTO в тикете OPS.
