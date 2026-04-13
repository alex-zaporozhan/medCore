# Поток 1e + Phase 3+ + опциональная Phase 4

> **1e:** [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md), МП §24.  
> **3+:** [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md), §25, ADR-010.  
> **4 (опция):** [09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md), §26, ADR-013.  
> **Индекс:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).  
> **PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-I1** (опция; отдельный go при продаже).

Стабилизировать **ядро** (1a–1c, контур B, §17.1) до крупных вложений в импорт и Commerce.

## QA_ARCH: префлайт для @ARCH и приёмка

**Цикл:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md). Инспектор: [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **PRC-I1:** опции **вне** базового L3 — отдельный go и отдельный **QA_REPORT** при продаже.

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до @DEV** | До старта **1e/3+/4**: явная запись «ядро стабилизировано» (ссылка на **PRC** или backlog-строки) или **ADR риска**. На **каждый** крупный срез: bounded context (границы модулей, `organization_id` / `clinic_id`), **PII** и audit, список **entitlement keys** в scope. **Phase 4:** отдельный арх-док перед миграциями Commerce ([09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md)). |
| **Минимум в `QA_REPORT`** | Негативы на утечку данных **cross-tenant** / cross-org для функций среза; для embed/RAG — ссылка на изоляцию из [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md) при пересечении. |
| **Красные флаги** | Импорт/Commerce «с нуля» без матрицы сущностей; тихие таблицы вне ADR; совмещение **§25** конвейера с биллингом без явной схемы. |

## 1e — срезы (из PHASE_FULL_CLOSURE 1e-F*)

| ID | Тема |
|----|------|
| 1e-F1 | RAG per-org (см. отдельно [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md)) |
| 1e-F2 | AI sanitizer + tokenizer-лимиты |
| 1e-F3 | UI экспорта / offboarding |
| 1e-F4 | Audit embed keys / webhook secret |
| 1e-F5 | RBAC сузить управление embed |
| 1e-F6 | Grafana/alerts по embed публичному контуру |
| 1e-F7 | Reverse-proxy лимит тела inbox |

## 3+ — срезы

- Конвейер импорта §25.0 (ingest → validate → clean → staging → commit) вместо заглушек.
- Audit смены `industry_profile` и крупных шагов импорта.
- Выравнивание effective organization на маршрутах (**3-F3** и др.).

## Phase 4

- Только после **go** ARCH: bounded context Commerce, `commerce.store_network`, совместимость с §25.

---

**Версия:** 2026-04-07.
