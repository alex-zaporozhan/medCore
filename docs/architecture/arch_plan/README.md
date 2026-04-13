# Архитектурный план исполнения SaaS (по мастер-плану)

> **Роль папки:** единая точка входа для **@ARCH → @DEV**: поэтапные архитектурные обязательства, порядок работ, ссылки на ADR и существующие спеки. Источник истины по продукту и воротам остаётся [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) (далее — **МП**).

**Сводный глобальный документ:** [MASTER_ARCH_PLAN.md](./MASTER_ARCH_PLAN.md).

## Как читать @DEV

1. Прочитать [00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md](./00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md) (15–20 мин.) — слои, зависимости фаз, **ворота §19 МП**.
2. Открыть [DEV_EXECUTION_SEQUENCE.md](./DEV_EXECUTION_SEQUENCE.md) — **порядок работ** (что параллельно, что блокирует).
3. Углубиться в файл фазы, с которой стартует эпик (см. таблицу ниже).

## Карта файлов ↔ фазы МП §15

| Файл в `arch_plan/` | Фаза МП | Якоря МП |
|---------------------|---------|----------|
| [01_PHASE_0_PREPARATION.md](./01_PHASE_0_PREPARATION.md) | Phase 0 (Docs) | §15, §18, §19, §23 |
| [02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md) | 1a Platform Core | §1, §6 (часть), §16.1, ADR-007, §17.1 |
| [03_PHASE_1B_COMMERCE_AND_UX.md](./03_PHASE_1B_COMMERCE_AND_UX.md) | 1b Commerce UI | §3–§8, §6, §10, ADR-011, §15c |
| [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) | 1c Entitlements | §12–§13, §16.5 |
| [05_PHASE_1D_OBSERVABILITY.md](./05_PHASE_1D_OBSERVABILITY.md) | 1d Observability | §11 |
| [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md) | 1e Lifecycle + Embed | §24, §15b 1e |
| [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md) | Phase 2 | §16.2–16.3, ADR-008/009, U-007–009 |
| [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md) | Phase 3+ | §14, §25, ADR-010 |
| [09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md) | optional_late_Commerce | §26, МП mermaid `p4` |
| [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) | Сквозное | §27–§31, §15a, §15b усиление |

Дополнительно:

- [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — **долг сверх DoD** по фазам (полное закрытие vs минимум; QA_ARCH / @ARCH).
- [TRACEABILITY_MATRIX.md](./TRACEABILITY_MATRIX.md) — трассировка разделов МП → артефакты репозитория.
- [TARIFF_ENTITLEMENT_RBAC_OWNER_ADMIN.md](./TARIFF_ENTITLEMENT_RBAC_OWNER_ADMIN.md) — мост «конструктор тарифа / договор» ↔ `organization_entitlements` ↔ RBAC ↔ админка Владельца.
- [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) — **Epic_ID** ↔ МП § ↔ backlog ↔ ADR ↔ код ↔ QA_REPORT; дорожные карты потоков: [STREAM_1A_PLATFORM_EPICS.md](./STREAM_1A_PLATFORM_EPICS.md), [STREAM_1B_COMMERCE_EPICS.md](./STREAM_1B_COMMERCE_EPICS.md), [STREAM_FRONTEND_SAAS_EPICS.md](./STREAM_FRONTEND_SAAS_EPICS.md), [STREAM_PHASE2_RELIABILITY_EPICS.md](./STREAM_PHASE2_RELIABILITY_EPICS.md), [STREAM_1E_AND_PHASE3_PLUS_EPICS.md](./STREAM_1E_AND_PHASE3_PLUS_EPICS.md), [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md).
- [DEV_EXECUTION_SEQUENCE.md](./DEV_EXECUTION_SEQUENCE.md) — **последовательность задач** и параллельные потоки P0.

## Связь с playbook LEAD

- [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md) — ритуал эпиков ARCH → DEV → QA_ARCH.
- [LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md](../LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md) — углубление узла Phase 0.

## Версия набора

- **2026-04-05** — первичная выкладка по МП §1–§31 и дорожной карте §15; добавлен [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (долг полного закрытия фаз).
