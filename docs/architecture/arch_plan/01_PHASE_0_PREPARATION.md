# Фаза 0 — подготовка документов и согласований (Phase_0_Docs)

**Узел МП:** `Phase_0_Docs` / D0 в [§15](../SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-15).  
**Цель:** закрыть неопределённости до необратимых миграций и публичного периметра; выровнять ADR, журнал U-*, рубрику.

## Архитектурные результаты фазы (Definition of Ready)

1. **ADR-007** — зафиксирован fork: RLS vs жёсткая политика в репозиториях + негативные тесты; граница platform/tenant (отдельная схема/набор таблиц или эквивалент).
2. **ADR-011** + **ADR-012** — контур B: провижининг вперёд (ADR-011) и **политика** возврата / chargeback / org после «денег назад» (ADR-012); реализация кода ADR-012 — бэклог фаз (см. **03_PHASE_1B**).
3. **Ключи entitlement** — согласованы с МП **§4**, **§13.1**, **§16.5**, **§24** (список не противоречит каталогу).
4. **U-005** — черновик целевой семантики `/owner/*` vs «сеть клиник» (не расширять API до решения).
5. **§17.1** — выбран и записан в `docs/operations` вариант (outbox / одна реплика / ADR риска) для целевого `replicas(API) ≥ 2`.
6. **INDEX / CONVENTIONS** — готовы к появлению новых префиксов ([CONVENTIONS_AND_TRACEABILITY.md](../CONVENTIONS_AND_TRACEABILITY.md)).

## Задачи @DEV (обычно минимальны на фазе 0)

- Поддержать **grep-аудит** текущих webhook/платежных путей для отчёта @ARCH (факт A vs B) — артефакт: [WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](../../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md) (**файл в репозитории**).
- Не начинать **новые** platform-миграции без записи по МП **§18**.

## Задачи @ARCH

- Провести **crash-review** с МП + [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) + [ENTERPRISE_SAAS_RUBRIC.md](../ENTERPRISE_SAAS_RUBRIC.md) (МП §19 п.4, §20).
- Обновить или создать **envelope** черновик (МП §31) — хотя бы таблица допущений.

## Связанные документы

- [LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md](../LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md)
- [docs/adr/README.md](../../adr/README.md)
- [UNRESOLVED_AND_CONFUSION_LOG.md](../UNRESOLVED_AND_CONFUSION_LOG.md)

## Выход из фазы

Явное **go** от @LEAD/@ARCH на старт **1a** (письменно: тикет или запись в ADR). После go — см. прогресс в [02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md) (секция «Статус @DEV»).
