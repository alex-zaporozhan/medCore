# FILE MAP — выборочный перечень `.md` (срез для RAG)

> **Версия:** 2026-04-10 (@QA_ARCH: содержание сверено; исправлены §4 и §6)  
> **Назначение:** ориентир для индексации и ссылок. **Не** исчерпывающий список всех markdown репозитория: в git сотни файлов под `docs/**`, `documentation/**` и корнем (glob `*.md` / `**/*.md`). §3 ниже — только **корень** `docs/*.md` без подпапок (`docs/architecture/`, `docs/frontend/`, `docs/artifacts/`, …). Для полного инвентаря — поиск по репозиторию или отдельная автоматизация.  
> **Приоритет истины:** **код** → **`docs/product_state/*.md`** → прочий `docs/`. Регламент пересчёта чисел в паспортах: [`PRODUCT_STATE_VERIFICATION.md`](./PRODUCT_STATE_VERIFICATION.md).

---

## 1. Корень репозитория

| # | Путь |
|---|------|
| 1 | `README.md` |
| 2 | `CONTRIBUTING.md` |
| 3 | `DOCUMENTATION_POLICY.md` |
| 3a | `CI_CD.md` |
| 3b | `AGENTS.md` |

---

## 2. Инфраструктура и прочее (вне `docs/`)

| # | Путь |
|---|------|
| 4 | `alembic/versions/README.md` |
| 5 | `deploy/grafana/README.md` |
| 6 | `.github/pull_request_template.md` |
| 7 | `src/scripts/dev/README.md` |

---

## 3. `docs/` — процесс, роли, шаблоны (алфавит)

| # | Путь |
|---|------|
| 8 | `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md` |
| 9 | `docs/ARCH_AUDIT_NEXT.md` |
| 10 | `docs/ARCH_FRONTEND_UI_LOGIC.md` |
| 11 | `docs/CACHE_STRATEGY.md` |
| 12 | `docs/CRYSTALS.md` |
| 13 | `docs/DEPLOY_LICENSE_AND_PIRACY.md` |
| 14 | `docs/DEPLOY_VPS_STEP_BY_STEP.md` |
| 15 | `docs/DEVELOPMENT_PLAN.md` |
| 16 | `docs/DOC_TOPOLOGY.md` |
| 17 | `docs/DOCKER_INFRA_PASSPORT.md` |
| 18 | `docs/DOMAIN_STANDARDS.md` |
| 19 | `docs/ENGINEERING_PLAN.md` |
| 20 | `docs/LEAD_ANTI_CHECKBOX_PROTOCOL.md` |
| 21 | `docs/LEAD_PRODUCT_GATE_PROTOCOL.md` |
| 22 | `docs/LEAD_PRODUCT_LOGIC_EXCELLENCE.md` |
| 23 | `docs/METRICS_PROTOCOL.md` |
| 24 | `docs/MIGRATION_UPGRADE.md` |
| 25 | `docs/NONFUNCTIONAL_SCORECARD.md` |
| 26 | `docs/PROCESS_LAUNCH.md` |
| 27 | `docs/PRODUCT_DOSSIER_BUYER_READY.md` |
| 28 | `docs/RAG_CANON.md` |
| 29 | `docs/README.md` |
| 30 | `docs/ROADMAP_VALUE_TO_PRICE.md` |
| 31 | `docs/RUN_SERVICES.md` |
| 32 | `docs/SEC_RBAC_SPEC.md` |
| 33 | `docs/SEED_PROTOCOL.md` |
| 34 | `docs/STACK_SELECTION.md` |
| 35 | `docs/TEMPLATE_ADMIN_UI_UX.md` |
| 36 | `docs/TEMPLATE_BIZ_LOGIC.md` |
| 37 | `docs/TEMPLATE_COMMERCIAL_PACK.md` |
| 38 | `docs/TEMPLATE_DESIGN_UX.md` |
| 39 | `docs/TEMPLATE_ERP_REPORTING_VITRINES.md` |
| 40 | `docs/TEMPLATE_MODULE_DEV.md` |
| 41 | `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` |
| 42 | `docs/TESTING_CANON.md` |
| 43 | `docs/TPF_MASTER.md` |
| 44 | `docs/TPF_MODULE_CRM.md` |
| 45 | `docs/TPF_MODULE_DASHBOARD.md` |
| 46 | `docs/TPF_MODULE_ENTITIES.md` |
| 47 | `docs/TPF_MODULE_FINANCE.md` |
| 48 | `docs/TPF_MODULE_FORMS.md` |
| 49 | `docs/TPF_MODULE_LOYALTY.md` |
| 50 | `docs/TPF_MODULE_OMNICHAT.md` |
| 51 | `docs/TPF_MODULE_PWA.md` |
| 52 | `docs/TPF_MODULE_SCHEDULE.md` |
| 53 | `docs/TPF_MODULE_SHELL.md` |
| 54 | `docs/TPF_MODULE_TASKS.md` |
| 55 | `docs/VALUATION_CODE_BACKED.md` |
| 56 | `docs/ROLE_ARCH.md` |
| 57 | `docs/ROLE_AUDITOR.md` |
| 58 | `docs/ROLE_BIZ.md` |
| 59 | `docs/ROLE_CREATOR.md` |
| 60 | `docs/ROLE_DESIGN.md` |
| 61 | `docs/ROLE_DEV.md` |
| 62 | `docs/ROLE_DOMAIN_EXPERT.md` |
| 63 | `docs/ROLE_FRONTEND.md` |
| 64 | `docs/ROLE_LAWYER.md` |
| 65 | `docs/ROLE_LEAD.md` |
| 66 | `docs/ROLE_OPS.md` |
| 67 | `docs/ROLE_PERF.md` |
| 68 | `docs/ROLE_PRINCIPLE.md` |
| 69 | `docs/ROLE_QA.md` |
| 70 | `docs/ROLE_QA_ARCH.md` |
| 71 | `docs/ROLE_SCRIBE.md` |
| 72 | `docs/ROLE_SEC.md` |

---

## 4. `docs/product_state/` — слой S (истина о продукте по коду)

| # | Путь |
|---|------|
| 73 | `docs/product_state/README.md` |
| 74 | `docs/product_state/INDEX.md` |
| 75 | `docs/product_state/BACKEND_PASSPORT.md` |
| 76 | `docs/product_state/FRONTEND_PASSPORT.md` |
| 77 | `docs/product_state/ARCHITECTURE_FROM_CODE.md` |
| 78 | `docs/product_state/PROJECT_STRUCTURE_FROM_CODE.md` |
| 79 | `docs/product_state/COMMERCIAL_VALUE_FROM_CODE.md` |
| 80 | `docs/product_state/FILE_MAP_MARKDOWN.md` (этот файл) |
| 81 | `docs/product_state/RAG_NECESSARY_IMPROVEMENTS.md` |
| 82 | `docs/product_state/QA_ARCH_RAG_AUDIT.md` |
| 83 | `docs/product_state/baselines/README.md` |
| 84 | `docs/product_state/RAG_NAVIGATION_S_LAYER.md` |
| 85 | `docs/product_state/CLIENT_STRUCTURE_AND_VALUE.md` |
| 86 | `docs/product_state/PRODUCT_STATE_VERIFICATION.md` |
| 87 | `docs/product_state/baselines/rbac_router_permissions.txt` (не `.md`; baseline для RBAC) |

### 4.1. Автогенерация (markdown, по желанию в индексе RAG)

| Путь | Как обновлять |
|------|----------------|
| `docs/product_state/generated/router_surface/INDEX.md` | `python scripts/generate_router_surface_docs.py` |

---

## 5. Итого (срез)

- В таблицах §1–§4 перечислены **основные** якорные пути; это **не** полное число markdown в репозитории.
- Плюс автоген: **`docs/product_state/generated/router_surface/INDEX.md`** (пересчёт: `scripts/generate_router_surface_docs.py`).
- Новые файлы слоя S добавляйте в §4 и в [`INDEX.md`](./INDEX.md) / [`README.md`](./README.md).

---

## 6. Каталоги с markdown вне §3 (ориентир)

В репозитории **присутствуют** (среди прочего):

- `documentation/` — пользовательский контур (`DOCUMENTATION_POLICY.md`).
- `docs/artifacts/` — слой W (процесс, QA, spine; не источник истины о рантайме).
- `docs/architecture/`, `docs/adr/`, `docs/frontend/`, `docs/operations/`, `docs/design/`, `docs/review/` — см. [`../DOC_TOPOLOGY.md`](../DOC_TOPOLOGY.md).

Полный список `.md` здесь **не** поддерживается вручную; для аудита ссылок — workflow **Documentation markdown links** (`.github/workflows/documentation-markdown-links.yml`).
