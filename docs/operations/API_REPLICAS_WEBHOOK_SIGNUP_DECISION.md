# Решение §17.1: мультиреплика API, публичный webhook B и signup

> **Источник:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §17.1 (PRINCIPLE §8).  
> **Владельцы:** ARCH предлагает, LEAD утверждает, OPS фиксирует в эксплуатации.

## Статус записи (governance)

Текст ниже — **рабочая фиксация для Phase 0** (DEV/QA_ARCH), чтобы не блокировать документы при отсутствии отдельного тикета. Он **не заменяет** явное подтверждение **LEAD** (продуктовый риск) и **OPS** (факт `replicas(API)` и правила ingress). Рекомендуется строка в релизном тикете: «§17.1 прочитан, путь согласован» + дата.

| Поле | Значение |
|------|----------|
| Дата черновика в репо | 2026-04-05 |
| Дата обновления (код + QA_ARCH) | 2026-04-08 |
| Подтверждение OPS (факт реплик / ingress) | _заполнить при первом multi-replica деплое с контуром B_ |
| Подтверждение LEAD | **Шаблон:** «Путь §17.1 согласован: outbox включён для контура B / или зафиксирован sticky singleton / или waiver ADR риска» + дата + ссылка на тикет. **Репозиторий (2026-04-08):** п.1 по коду закрыт — `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED` по умолчанию включает outbox-провижининг; runtime-подпись OPS/LEAD — при первом деплое с `replicas(API) ≥ 2`. |

## Закрытие PRC-E1 в репозитории (QA_ARCH)

- **Код:** hot-path «оплачено → провижининг» для контура B идёт через transactional outbox + `dispatch_domain_outbox_batch` / Celery (см. таблицу «Факт кода» ниже и `platform_subscription_billing.md` §10).
- **Процесс:** строки «Подтверждение OPS / LEAD» в governance-таблице выше — **не** дублируют CI; их заполняют при переводе staging/prod на горизонтальное масштабирование API с публичным webhook B. До этого момента достаточно ссылки на этот документ и зелёного pytest/outbox-тестов.

## Проблема

При `replicas(API) ≥ 2` запрос может закоммитить транзакцию на одной реплике, а побочные эффекты (in-process `EventBus`, отложенный провижининг) ожидать другой инстанс. Для **публичного** контура **B** (подписка платформы) и критичного **signup** это даёт класс риска: «оплата подтверждена — провижининг не доехал».

## Допустимые пути (один должен быть явно выбран до масштабирования)

1. **Минимальный outbox** (или эквивалент с идемпотентным consumer) для hot-path платёж → провижининг org — см. [ADR-009](../adr/ADR-009-async-outbox-event-delivery.md), мастер-план §16.2–§16.3, Фаза 2.
2. **Операционный режим:** webhook **B** и/или публичный signup принимаются только **одной** выделенной репликой (sticky ingress / отдельный сервис-вход / документированный SPOF) **до** внедрения п.1; дата пересмотра — в runbook OPS.
3. **ADR риска** с перечислением принятых потерь и сроком пересмотра (если сознательно идём в multi-replica без п.1–2).

## Зафиксированный выбор на дату Phase 0 (2026-04-05)

| Среда | Выбор | Примечание |
|-------|--------|------------|
| **Локальная разработка / типичный compose** | П.2 *де-факто* (один процесс API) | Достаточно для MVP spine контура B. |
| **Staging / prod до внедрения outbox по ADR-009 для hot-path B** | **П.2** — не масштабировать горизонтально **приём** `POST …/platform/billing/webhooks/*` и критичного публичного signup без выделенного singleton-входа **или** без П.1 | OPS подтверждает факт `replicas(API)` и правила ingress в [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md). |
| **Целевое состояние** | **П.1** | Перед платным self-service без ручного провижининга — согласно §16.6 и ADR-011. |

### Факт кода (Phase 2 / 2-E1, 2026-04-06)

При **`DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED=true`** (дефолт) после `succeeded` в транзакции webhook пишется строка `domain_outbox` с `event_type=PlatformSignupProvision` и `dedup_key=platform_signup_provision:{intent_id}`; провижининг выполняется в `dispatch_domain_outbox_batch` (сразу после первого commit webhook и периодически Celery `domain_outbox.dispatch_pending`). Семантика доставки провижининга: **at-least-once** относительно триггера «оплачено»; идемпотентность — `execute_platform_provision`. При **`false`** сохраняется прежний двухфазный sync-провижининг во второй транзакции того же запроса (как до 2-E1).

**Повторная оценка:** при добавлении нового публичного денежного или провижининг-пути — перечитать §17.1 и обновить таблицу выше.

## Связанные артефакты

- [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md) — контур B, MVP spine vs §16.6.  
- [DEV_EXECUTION_SEQUENCE.md](../architecture/arch_plan/DEV_EXECUTION_SEQUENCE.md) — шаг 0, параллельные потоки P0.  
- [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../architecture/FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) — транзакции vs события.
