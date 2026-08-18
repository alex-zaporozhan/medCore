# Архив: ERP vNext — волны планирования и QA_ARCH (2026)

Каталог **`erp-vnext-2026-wave-planning`** — не исполняемый бэклог, а **исторический пакет**: доменные чертежи `ARCH_*_NEXT.md`, волны `DEV_PROMPT_QA_ARCH_*`, пост-волновой фундамент, техпаспорта фронта, L2 perf/ops и связанные материалы. Он дополняет живой слой **`docs/artifacts/`** (бизнес-канон, SaaS spine) и **`docs/architecture/`** / **`docs/adr/`**.

## Зачем это в репозитории

- **RAG и онбординг:** даёт контекст «откуда взялись» доменные границы, волны усиления и формулировки DoD, не дублируя код.
- **Трассировка:** ссылки из **`docs/product_state/`**, **`docs/artifacts/`** и handover могут указывать сюда как на **источник намерений**, а код и ADR — как на **источник правды**.

## Канонические пути (актуальное)

| Нужно | Где |
|--------|-----|
| Бизнес-логика и маршруты (живой канон) | [`docs/artifacts/BUSINESS_LOGIC.md`](../../artifacts/BUSINESS_LOGIC.md), [`docs/artifacts/BUSINESS_ROUTES.md`](../../artifacts/BUSINESS_ROUTES.md) |
| Архитектура «как в коде» и ADR | [`docs/handover/02_architecture_and_decisions.md`](../../handover/02_architecture_and_decisions.md), [`docs/adr/README.md`](../../adr/README.md) |
| План исполнения SaaS / фазы | [`docs/architecture/arch_plan/MASTER_ARCH_PLAN.md`](../../architecture/arch_plan/MASTER_ARCH_PLAN.md) |
| RBAC-спека и инвентарь | [`docs/SEC_RBAC_SPEC.md`](../../SEC_RBAC_SPEC.md), [`documentation/rbac_router_permissions.txt`](../../../documentation/rbac_router_permissions.txt) |
| CI/CD | Корневой [`CI_CD.md`](../../../CI_CD.md), [`AGENTS.md`](../../../AGENTS.md) |

## Исторические имена файлов

В текстах пакета встречаются **`BUSINESS_LOGIC_CURRENT.md` / `BUSINESS_LOGIC_V2.md`**: отдельных файлов с такими именами в репозитории **нет**; фактический канон — **`docs/artifacts/BUSINESS_LOGIC.md`**, целевые доменные расширения vNext — в **`ARCH_*_NEXT.md`** этого каталога.

Внешнее ТЗ **`REDISIGN_FRONT.md`** в git не хранится (политика длинных пакетов — см. корневой [`docs/archive/README.md`](../README.md)).

## Оглавление пакета

См. **[INDEX.md](./INDEX.md)** — классификация файлов по типу (архитектура, QA, gaps, runbooks).

## Ссылки между файлами

Внутренние перекрёстные ссылки ведут на соседние файлы (`./ИМЯ.md`). Ссылки на документы вне каталога используют относительные пути вида `../../…` и проверяются CI **`documentation-markdown-links.yml`**.
