# Актуальные артефакты продукта и архитектуры (2026)

**С чего начать:** **[ARTIFACT_MAP.md](./ARTIFACT_MAP.md)** — ID **S-00…S-07**, **A-00…A-02**, **P-00…P-07**. Программа **8.5+ (будущее)** — **[`85 plus/README.md`](./85%20plus/README.md)**. Устаревшие копии — **`archive/`** (внутри `artifacts/`) и **`archive/_outdated/`** (см. карту §4). Краткий индекс `docs/archive/` — **[`../archive/README.md`](../archive/README.md)**.

## Канон продукта (S)

| ID | Документ |
|----|----------|
| **S-00** | [ARTIFACT_MAP.md](./ARTIFACT_MAP.md) |
| **S-01** | [MASTER_PRODUCT_ROADMAP_2026.md](./MASTER_PRODUCT_ROADMAP_2026.md) |
| **S-02** | [PRODUCT_IA_RBAC_NAVIGATION_2026.md](./PRODUCT_IA_RBAC_NAVIGATION_2026.md) |
| **S-03** | [PRODUCT_PASSPORT_UX_DESIGN_BACKEND_2026.md](./PRODUCT_PASSPORT_UX_DESIGN_BACKEND_2026.md) |
| **S-04** | [SME_BOX_NFR_CHECKLIST.md](./SME_BOX_NFR_CHECKLIST.md) |
| **S-05** | [ARCHITECTURE_ATLAS_2026.md](./ARCHITECTURE_ATLAS_2026.md) |
| **S-06** | [DEV_EXECUTION_PLAYBOOK_2026.md](./DEV_EXECUTION_PLAYBOOK_2026.md) |
| **S-07** | [TZ_COVERAGE_MATRIX_2026.md](./TZ_COVERAGE_MATRIX_2026.md) |

## Канон @ARCH (A + P)

| ID | Документ |
|----|----------|
| **A-00** | [ARCH_INDEX_PHASES_2026.md](./ARCH_INDEX_PHASES_2026.md) — индекс фаз **P-00…P-07** |
| **A-01** | [ARCH_CROSS_CUTTING_UI_I18N_2026.md](./ARCH_CROSS_CUTTING_UI_I18N_2026.md) — модалки, русский UI |
| **A-02** | [ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md](./ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md) — данные, бэкапы, мультитенантность |

Файлы фаз: `ARCH_PHASE_00_FOUNDATION_2026.md` … `ARCH_PHASE_07_ENTERPRISE_RESUME_2026.md` (список в A-00).

**P1 Staff Core — что сделано в коде (зафиксировано):** `ARCH_PHASE_01_STAFF_CORE_2026.md` §9 (статус по темам) и **§10** (таблица ссылок на модули в репозитории).

## NFR (проект)

| Документ | Путь |
|----------|------|
| Scorecard | `docs/NONFUNCTIONAL_SCORECARD.md` |
| Первый прогон @LEAD / ops | `docs/operations/LEAD_FIRST_RUN_OPS.md` |
| Тестовая БД для pytest (`dental_booking_test`) | [`docs/development/TEST_DATABASE.md`](../development/TEST_DATABASE.md) |
| Бэклог NFR (после коробки v1) | `docs/operations/BACKLOG_NFR.md` |
| Единый бэклог QA_ARCH «на потом» (triage) | [`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`](./QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md) |
| Мини-эпик follow-up P2 после ревью @QA_ARCH | [`QA_ARCH_P2_CLIENTS_SCHEDULE_FOLLOWUP_2026.md`](./QA_ARCH_P2_CLIENTS_SCHEDULE_FOLLOWUP_2026.md) |
| QA_ARCH roadmap 8.5+ (полка «на будущее») | [`docs/artifacts/85 plus/QA_ARCH_85_PLUS_ROADMAP.md`](./85%20plus/QA_ARCH_85_PLUS_ROADMAP.md) |
| Staff chat: мультитенантность и политика сети | `docs/architecture/STAFF_CHAT_MULTITENANCY.md` |
| Enterprise: сеть салонов + общий чат (план) | `ENTERPRISE_STAFF_NETWORK_AND_CHAT_2026.md` |
| Enterprise: уволенные, карточки персонала, места (план) | `ENTERPRISE_STAFF_LIFECYCLE_CARDS_2026.md` |

## Полка **85 plus** (8.5+, на будущее)

См. [`85 plus/README.md`](./85%20plus/README.md) и [ARTIFACT_MAP.md §4](./ARTIFACT_MAP.md).

## Архив и `_outdated`

См. [ARTIFACT_MAP.md §5](./ARTIFACT_MAP.md). Папка `_outdated` в `.cursorignore`.

## Процесс

`docs/ENGINEERING_PLAN.md`, `.cursorrules.md`. При конфликте — согласованные документы **S-*** и **A-***.
