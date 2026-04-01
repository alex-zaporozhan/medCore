# LEAD_DB_CACHE_AUDIT — аудит БД и кэша для мультиклиники/Enterprise

> **Роль:** @LEAD  
> **Цель:** зафиксировать фактическое состояние контуров DB/Redis/Celery, ранжировать риски L1/L2/L3 и задать обязательный hardening с владельцами и сроками.  
> **Статус:** operational artifact для включения в 8W execution tracker.

---

## 1) Уровни риска (L1/L2/L3)

| Уровень | Интерпретация | Политика |
|--------|----------------|----------|
| L1 | Локальная деградация без потери бизнес-инвариантов | исправление в плановом цикле |
| L2 | Риск срыва SLA/операций по контуру | фикс в ближайшем спринте, контроль @OPS |
| L3 | Integrity/commercial breach (утечки/финансы/tenant bypass) | stop-release до исправления |

---

## 2) Реестр контуров DB/Cache (факт -> риск -> hardening)

| Контур | Текущая реализация (факт) | Риск | Hardening | Owner | Срок |
|-------|----------------------------|------|-----------|-------|------|
| Payments authz boundary | Создание платежа по `booking_id`, контекст допускает `system` fallback; проверка владельца/клиники вызывающего не жёстко зафиксирована | **L3** | Обязательный authz gate: `booking` должен принадлежать субъекту токена и его tenant scope; запрет безтокенного create-payment | DEV + QA_ARCH | Week 1 |
| Booking slot uniqueness | DB unique по `(doctor_id, date, time)`; отмены/повторы зависят от статусов и app-логики | **L2** | Синхронизировать DB policy и доменную модель: partial unique (active-only) или иная формальная политика слота + concurrency regression suite | ARCH + DEV | Week 3 |
| Transaction chain Booking->Payment->ERP | Внешний провайдер + локальные записи без 2PC; согласованность достигается webhook/retry-path | **L2** | Reconciliation job + outbox/inbox + idempotency ключи в event-path | DEV + OPS | Week 3-4 |
| Tenant isolation in repositories | Основной контроль на app-уровне (`clinic_id`, guards), не DB-RLS | **L2** | Audit всех `get_by_id`/list путей; обязательные `for_clinic` методы для чувствительных сущностей; tenant leak tests API+jobs | QA_ARCH + DEV | Week 7 |
| Schedule Redis cache keys | Ключ `schedule:{doctor_id}:{day}`, TTL 300, clinic guard выполняется перед cache read | **L1** | Формализовать policy: когда `clinic_id` обязателен в ключе; добавить миграционный сценарий для doctor-clinic reassignment | ARCH + DEV | Week 2 |
| Cache invalidation resilience | Инвалидация best-effort, при Redis сбоях допускается временный stale | **L1** | Ввести метрику stale-window и alert, добавить forced rebuild path для критичных read-маршрутов | OPS + DEV | Week 5 |
| ERP report cache namespace | Ключи namespaced по `clinic_id`, есть инвалидация по префиксу | **L1** | Добавить smoke на invalidation completeness + bounded freshness SLO | DEV + QA_ARCH | Week 5-6 |
| Rate limiter Redis fail-open | При ошибке Redis ограничения не блокируют запросы | **L2** | Разделить policy: критичные auth/payment пути fail-closed или strict fallback; прочие остаются fail-open | ARCH + OPS | Week 2 |
| Celery reminders periodic task | Риск ошибки сигнатуры/вызова периодической задачи и нет жёсткого теста beat execution | **L2** | Привести task signature к корректной bind-модели и добавить beat regression test | DEV | Week 1 |
| Reminders/notifications dedup | Fanout reminder-задач без глобального идемпотентного ключа на доставку | **L2** | Redis/DB dedup key `booking_id + reminder_type + window`; delivery idempotency proof в тестах | DEV + QA_ARCH | Week 2-3 |
| Queue isolation and routing | Единая default queue для разнотипных задач (операционные/тяжёлые) | **L2** | Разделить очереди и лимиты worker concurrency (critical vs heavy); добавить queue lag SLO по классам | OPS + DEV | Week 6 |
| Export/backup status keys | Статусы в Redis по `task_id`, без явного `clinic_id` namespace | **L1** | Добавить tenant-aware валидацию доступа к task status и префикс по clinic при необходимости | DEV | Week 4 |
| Alembic drift control | Риск расхождения ORM и схемы при неполной миграционной дисциплине | **L2** | CI gate на schema drift (`alembic upgrade head` + diff check), запрет релиза при drift | DEV + QA_ARCH | Week 1 |
| DB/Redis capacity guardrails | Базовые лимиты есть, но нужны эксплуатационные пороги по росту нагрузки | **L2** | Capacity envelope: pool saturation, queue lag, redis evictions, alert thresholds и runbook действий | OPS | Week 6 |

---

## 3) Первичная приоритизация P0/P1/P2 (на ближайший релиз)

### P0 (обязательно до ближайшего prod релиза)

| Контур | Почему P0 | Минимальный критерий закрытия |
|--------|-----------|-------------------------------|
| Payments authz boundary | Прямой L3 риск финансового/tenant bypass | negative tests + runtime guard: создание оплаты только для допустимого субъекта/клиники |
| Alembic drift control | Риск выкатить несовместимую схему/код | CI блокирует release при schema drift |
| Celery reminders periodic task | Риск silent-fail в критичном канале напоминаний | beat task выполняется стабильно, есть regression test |

### P1 (закрыть в следующем спринте после релиза)

| Контур | Почему P1 | Минимальный критерий закрытия |
|--------|-----------|-------------------------------|
| Transaction chain Booking->Payment->ERP | Риск частичных рассогласований в revenue цепочке | reconciliation отчёт + idempotent replay |
| Tenant isolation in repositories | Системный риск регрессии на app-level изоляции | audit + тестовый набор cross-tenant leak |
| Rate limiter Redis fail-open | При деградации Redis ослабевает защита критичных маршрутов | для auth/payment определена строгая policy (fail-closed/strict fallback) |
| Reminders/notifications dedup | Риск дублей уведомлений и шум/операционный ущерб | dedup ключи + тесты идемпотентности доставки |
| Queue isolation and routing | Тяжёлые задачи влияют на операционные контуры | отдельные очереди + SLO по lag для классов задач |

### P2 (плановое усиление, не блокер релиза при контроле рисков)

| Контур | Почему P2 | Минимальный критерий закрытия |
|--------|-----------|-------------------------------|
| Booking slot uniqueness | Нужна донастройка продуктовой политики слотов | формальная DB+domain policy и concurrency suite |
| Schedule Redis cache keys | Больше про устойчивость/эволюцию схемы, чем про текущий breach | policy по cache key namespace и сценарий reassignment |
| Cache invalidation resilience | Управляемость stale-окон | alert на stale-window + forced rebuild path |
| ERP report cache namespace | В целом зрелый контур, нужна эксплуатационная доводка | smoke invalidation + freshness SLO |
| Export/backup status keys | Локальный tenant-hardening для служебных ключей | tenant-aware validation на чтение статуса |
| DB/Redis capacity guardrails | Важный масштабный блок, но обычно не day-0 blocker | зафиксирован capacity envelope + runbook перегрузки |

---

## 4) Обязательные KPI для этого аудита

1. `tenant_scope_mismatch_count` = 0 на релизном smoke.
2. `booking_payment_erp_mismatch_rate` <= 0.5% за сутки.
3. `queue_lag_seconds_p95` в пределах agreed SLO.
4. `redis_evictions_total` не растёт в нормальном профиле нагрузки.
5. `payment_authz_violation_count` = 0 (negative tests + runtime signals).

---

## 5) Gate-условия (привязка к релизу)

1. Любой открытый **L3** пункт = `NO-GO`.
2. Для каждого **L2** пункта должен быть owner, срок и evidence прогресса.
3. Без тестового доказательства по payment authz/tenant isolation релиз не допускается.
4. DR/restore считается принятым только если post-restore smoke подтверждает ключевые DB/Cache цепочки.

---

## 6) Формат еженедельного обновления

| Неделя | Контур | Что закрыто | KPI delta | Остаточный риск | Следующий шаг |
|--------|--------|-------------|-----------|------------------|---------------|
| Week N | ... | ... | ... | ... | ... |

---

## 7) Связанные документы

- `QA_ARCH_85_PLUS_ROADMAP.md`
- `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`
- `LEAD_INTEGRATION_GATES.md`
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md`
