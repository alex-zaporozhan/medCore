# Envelope масштаба Enterprise SaaS (черновик @ARCH / @LEAD)

> **Статус:** черновик для расчётов индексов, пагинации и нагрузочных сценариев.  
> **Связь:** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §30–§31, [arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) §31, [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).

## Утверждённые ориентиры (до подписи @LEAD — не догма)

| Величина | Ориентир | Комментарий |
|----------|----------|-------------|
| Активных организаций | до **10 000** | Маркетинговый потолок плана |
| Точек на организацию | до **10** | Порядок **~10⁵** точек суммарно |
| Персонал | до **40** на точку **или** на организацию | Уточнить продукт — влияет на RBAC и сессии |
| Клиентов в БД | **5 000–10 000+** на организацию **или** на точку | Влияет на поиск, импорт, индексы |

### Подпись LEAD (PRC-G1)

Документ остаётся **черновиком ориентиров** до явной строки: «Утверждено для периметра релиза X» + дата + тикет. До этого **PRC-G1** в матрице Production Launch — `in_progress`, не `satisfied`.

| Поле | Значение |
|------|----------|
| Утверждено LEAD | _дата / тикет_ |
| Ограничения периметра | _например: до 500 org на первом платном релизе_ |

## Сценарий нагрузки (§30 — честность до заявлений «10k+»)

**Шаблон прогона и чеклист:** [../operations/LOAD_SCENARIO_MARKETING_10K.md](../operations/LOAD_SCENARIO_MARKETING_10K.md).

Перед публичными формулировками про RPS и одновременных пользователей зафиксировать отдельным прогоном (staging или отчёт):

1. **N** активных организаций и **M** RPS на критичные пути (логин админа, запись, webhook A/B, публичный embed).
2. Что меряем: `http_request_duration_seconds`, domain-метрики, lag outbox, ошибки БД.
3. Допущения: один регион, модульный монолит, Postgres + Redis, горизонталь API при stateless JWT.

**Ответственный:** @ARCH (черновик) + @LEAD (утверждение чисел). **Дата пересмотра:** по major SaaS-релизу или ежеквартально.

## Правила для @DEV

- Списки и отчёты — пагинация / keyset; без полного сканирования крупных таблиц без явного согласования.
- Метрики алертов — без сырого `organization_id` в лейблах ([07_metrics_observability.md](./07_metrics_observability.md)).
- Импорт и массовые операции — батчи, идемпотентность ([modules/data_migration_import_connectors.md](./modules/data_migration_import_connectors.md), МП §25.3).

## Статус @QA_ARCH (envelope §31)

Черновик и числа — этот документ; PRC-G1 / утверждение LEAD — [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (**0-F1**), [STREAM_PRODUCTION_READINESS.md](./arch_plan/STREAM_PRODUCTION_READINESS.md).
