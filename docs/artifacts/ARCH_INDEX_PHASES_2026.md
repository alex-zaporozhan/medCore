# ARCH_INDEX_PHASES_2026 — индекс фазовой архитектуры (@ARCH)

> **Назначение:** навигация по **одному документу на фазу** из `MASTER_PRODUCT_ROADMAP_2026.md` (S-01). Каждый файл — границы, данные, безопасность, мультитенантность, сквозные UI/i18n.

## Документы по фазам

| Фаза | Код | Файл |
|------|-----|------|
| 0 — Foundation | P0 | [ARCH_PHASE_00_FOUNDATION_2026.md](./ARCH_PHASE_00_FOUNDATION_2026.md) |
| 1 — Staff Core | P1 | [ARCH_PHASE_01_STAFF_CORE_2026.md](./ARCH_PHASE_01_STAFF_CORE_2026.md) |
| 2 — Clients & Schedule | P2 | [ARCH_PHASE_02_CLIENTS_SCHEDULE_2026.md](./ARCH_PHASE_02_CLIENTS_SCHEDULE_2026.md) |
| 3 — Omni-Chat PWA | P3 | [ARCH_PHASE_03_OMNI_CHAT_2026.md](./ARCH_PHASE_03_OMNI_CHAT_2026.md) |
| 3.1 — Hardening / Gate closure | P3.1 | [ARCH_PHASE_03_1_HARDENING_P0_P3_2026.md](./ARCH_PHASE_03_1_HARDENING_P0_P3_2026.md) |
| 4 — Marketing Box | P4 | [ARCH_PHASE_04_MARKETING_BOX_2026.md](./ARCH_PHASE_04_MARKETING_BOX_2026.md) |
| 5 — Analytics & Finance Box | P5 | [ARCH_PHASE_05_ANALYTICS_FINANCE_2026.md](./ARCH_PHASE_05_ANALYTICS_FINANCE_2026.md) |
| 6 — Owner & RBAC | P6 | [ARCH_PHASE_06_OWNER_RBAC_2026.md](./ARCH_PHASE_06_OWNER_RBAC_2026.md) |
| 7 — Post-Box Enterprise | P7 | [ARCH_PHASE_07_ENTERPRISE_RESUME_2026.md](./ARCH_PHASE_07_ENTERPRISE_RESUME_2026.md) |

### Бизнес-входы → @ARCH (P3 Omni)

| Документ | Назначение |
|----------|------------|
| [BIZ_TZ_OMNI_UNIFIED_INBOX_FOR_ARCH_2026.md](./BIZ_TZ_OMNI_UNIFIED_INBOX_FOR_ARCH_2026.md) | ТЗ: коммерческий unified inbox («много каналов — одно окно»), KPI, процессы, критерии приёмки архитектурного артефакта |

### Архитектура и реализация (P3 Omni — расширение)

| Документ | Назначение |
|----------|------------|
| [ARCH_OMNI_AGENT_WORKSTATION_2026.md](./ARCH_OMNI_AGENT_WORKSTATION_2026.md) | Gap analysis vs QA/BIZ, целевая стратегия и архитектура бэка/фронта (ядро, канальный слой, workstation) |
| [DEV_PROMPTS_OMNI_AGENT_WORKSTATION_2026.md](./DEV_PROMPTS_OMNI_AGENT_WORKSTATION_2026.md) | Промпты для @DEV: P0–P2 задачи с критериями готовности |
| [QA_ARCH_OMNI_PLANS_REVIEW_2026.md](./QA_ARCH_OMNI_PLANS_REVIEW_2026.md) | Аудит @QA_ARCH: соответствие планов целям, бизнесу, безопасности |

## Сквозные (все фазы)

| Тема | Файл |
|------|------|
| Модалки центр + русский UI | [ARCH_CROSS_CUTTING_UI_I18N_2026.md](./ARCH_CROSS_CUTTING_UI_I18N_2026.md) |
| БД, бэкапы, мультитенантность | [ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md](./ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md) |

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-25 | P3: добавлены `ARCH_OMNI_AGENT_WORKSTATION_2026.md`, `DEV_PROMPTS_OMNI_AGENT_WORKSTATION_2026.md`; таблица **Бизнес-входы → @ARCH** — `BIZ_TZ_OMNI_UNIFIED_INBOX_FOR_ARCH_2026.md` |
| 2026-03-24 | P1 Staff Core: в `ARCH_PHASE_01_STAFF_CORE_2026.md` добавлен **§10** — ссылки на модули в репозитории (перечень зафиксированной реализации) |
| 2026-03-24 | Создан индекс и фазовые документы |
