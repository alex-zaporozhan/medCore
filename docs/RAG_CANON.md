# RAG_CANON — порядок источников для AI

> **Версия:** 2026-04-09 (таблица §2: якоря фаз 6–8 в `frontend/PHASE_*.md`)  
> **Назначение:** одна страница «что читать в каком порядке», без ожидания удалённых каталогов и без подмены кода планами.

---

## 1. Жёсткий приоритет при противоречии

1. **Код и тесты** репозитория (`src/`, `frontend/src/`, `tests/`, `alembic/versions/`).  
2. **`docs/product_state/`** (слой **S**) — паспорта и карта markdown, выведенные из кода: начать с [`product_state/INDEX.md`](product_state/INDEX.md).  
3. **Остальной `docs/*.md`** (слой **P**) — роли, шаблоны, протоколы процесса, NFR-скоринг; **не** источник истины о том, что уже реализовано.  
4. **Слой W (`docs/artifacts/`)** — рабочие материалы волны: QA-отчёты, spine, `DEVELOPMENT_PLAN`, регистры; см. [`artifacts/README.md`](artifacts/README.md). **Не** источник истины о том, что уже в коде и в проде: при расхождении с **`docs/product_state/`** или с репозиторием — верить **коду и слою S**. RAG может индексировать W для контекста процесса и аудита, но не подменять паспорта из кода.  
5. **Каталог `documentation/`** — **пользовательский контур** (гайды, питч); не источник истины о коде. Инженерный канон — `docs/` + код. См. [`DOCUMENTATION_POLICY.md`](../DOCUMENTATION_POLICY.md).

Подробнее о слоях и правилах размещения: [`DOC_TOPOLOGY.md`](DOC_TOPOLOGY.md), [`product_state/README.md`](product_state/README.md).

---

## 2. По типу вопроса (маршрутизация)

| Вопрос | Сначала | Потом |
|--------|---------|--------|
| Как читать слой S по порядку (навигация RAG) | [`product_state/RAG_NAVIGATION_S_LAYER.md`](product_state/RAG_NAVIGATION_S_LAYER.md) | [`product_state/INDEX.md`](product_state/INDEX.md) |
| Что реально есть в продукте (API, модули, экраны) | [`product_state/BACKEND_PASSPORT.md`](product_state/BACKEND_PASSPORT.md), [`product_state/FRONTEND_PASSPORT.md`](product_state/FRONTEND_PASSPORT.md) | код роутеров и `App.tsx` |
| Конкретный экран SPA (цель, данные, RBAC, gap) | [`frontend/pages/README.md`](frontend/pages/README.md) → файлы в `docs/frontend/pages/`, критерии [`frontend/PAGE_PASSPORT_CRITERIA.md`](frontend/PAGE_PASSPORT_CRITERIA.md) | `App.tsx`, страница, хуки |
| Порядок эпиков @QA_ARCH, скрипт паспортов (`verify` / `generate`), чеклисты фаз 6–8 (C4–D3) | [`frontend/MASTER_FRONTEND_EXECUTION_PLAN.md`](frontend/MASTER_FRONTEND_EXECUTION_PLAN.md) | `scripts/gen_frontend_page_passport_stubs.py`, [`frontend/pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`](frontend/pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md), [`frontend/PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](frontend/PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md), [`frontend/PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](frontend/PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md), [`frontend/PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](frontend/PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md) |
| Единый стиль и зоны фронта | [`frontend/FRONTEND_ARCHITECTURE_CANON.md`](frontend/FRONTEND_ARCHITECTURE_CANON.md), [`frontend/UI_THEME.md`](frontend/UI_THEME.md) | `theme.ts`, layouts |
| Слои SPA, проверяемость доков, чеклист PR (фронт) | [`frontend/FRONTEND_ENGINEERING_CONVENTIONS.md`](frontend/FRONTEND_ENGINEERING_CONVENTIONS.md) | `hooks/`, `api/client.ts`, тесты `routePaths`, `adminNoRawMantineDrawer` |
| Архитектура и границы подсистем | [`product_state/ARCHITECTURE_FROM_CODE.md`](product_state/ARCHITECTURE_FROM_CODE.md) | `src/main.py`, `docker-compose.yml` |
| Дерево репозитория | [`product_state/PROJECT_STRUCTURE_FROM_CODE.md`](product_state/PROJECT_STRUCTURE_FROM_CODE.md) | фактический listing |
| Коммерческий смысл реализованного | [`product_state/COMMERCIAL_VALUE_FROM_CODE.md`](product_state/COMMERCIAL_VALUE_FROM_CODE.md) | только как интерпретация кода |
| Срез якорных `.md` и слой S в карте | [`product_state/FILE_MAP_MARKDOWN.md`](product_state/FILE_MAP_MARKDOWN.md) | полный инвентарь — поиск по репо, не только этот файл |
| Сверка чисел в паспортах с кодом (@QA_ARCH) | [`product_state/PRODUCT_STATE_VERIFICATION.md`](product_state/PRODUCT_STATE_VERIFICATION.md) | glob / grep по таблице в файле |
| Пробелы, риски, долг (не факты) | [`product_state/RAG_NECESSARY_IMPROVEMENTS.md`](product_state/RAG_NECESSARY_IMPROVEMENTS.md) | — |
| NFR, алерты, пороги | `docs/NONFUNCTIONAL_SCORECARD.md`, `docs/METRICS_PROTOCOL.md` | `deploy/prometheus/`, `deploy/grafana/` |
| Как работать по ролям | `docs/ROLE_*.md`, `docs/ENGINEERING_PLAN.md` | не смешивать с «что умеет код» |
| Запуск сервисов, миграции | `docs/RUN_SERVICES.md`, `docs/MIGRATION_UPGRADE.md` | `docker-compose.yml` |

---

## 3. Правила для модели (анти-галлюцинации)

| Правило | Деталь |
|---------|--------|
| `docs/artifacts/` | Файлы есть в git (слой W); не считать их автоматически актуальнее `product_state/` или кода. Spine и QA_REPORT — снимок волны, не инвентарь рантайма. |
| `documentation/` | Пользовательские материалы; для фактов о коде сверять с `docs/product_state/` и исходниками. |
| Код без ссылок на markdown | В `src/` и `frontend/src/` **не** должно быть ссылок на `.md` в комментариях и строках — канон в коде и в `docs/product_state/`. Исключение: только репозиторные markdown **вне** прикладного кода (README, docs, workflow). |
| Слой S не STUB | Файлы в `product_state/` считаются актуальными снимками; при сомнении сверять с кодом. |

---

## 4. Дубли: первичная точка при расхождении

- **Маршруты API** — `src/api/v1/router.py` + [`BACKEND_PASSPORT.md`](product_state/BACKEND_PASSPORT.md).  
- **Маршруты SPA** — `frontend/src/routePaths.ts`, `frontend/src/App.tsx` + [`FRONTEND_PASSPORT.md`](product_state/FRONTEND_PASSPORT.md); детализация экранов — [`frontend/pages/`](frontend/pages/).  
- **RBAC-коды** — `src/application/rbac_matrix.py`, `require_permissions` в роутерах, baseline `docs/product_state/baselines/rbac_router_permissions.txt` (после `python scripts/audit_rbac_endpoints.py --write`).  
- **UI / тема** — `frontend/src/theme.ts`, `frontend/src/index.css`, Mantine override (не вымышленные design-md).  
- **NFR-зрелость процесса** — `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md`; операционный запуск — `docs/RUN_SERVICES.md`, `deploy/grafana/README.md`.

---

## 5. Индекс

- Навигация слоя S (mermaid, вопрос→документ): [`product_state/RAG_NAVIGATION_S_LAYER.md`](product_state/RAG_NAVIGATION_S_LAYER.md)  
- Карта папок под `docs/`: [`DOC_TOPOLOGY.md`](DOC_TOPOLOGY.md)  
- Дедупликация источников по фронту: [`frontend/RAG_FRONTEND_SOURCE_MAP.md`](frontend/RAG_FRONTEND_SOURCE_MAP.md)  
- Инженерные соглашения SPA: [`frontend/FRONTEND_ENGINEERING_CONVENTIONS.md`](frontend/FRONTEND_ENGINEERING_CONVENTIONS.md)  
- Срез якорных markdown / слой S в карте: [`product_state/FILE_MAP_MARKDOWN.md`](product_state/FILE_MAP_MARKDOWN.md)  
- Сверка паспортов с кодом: [`product_state/PRODUCT_STATE_VERIFICATION.md`](product_state/PRODUCT_STATE_VERIFICATION.md)  
- Аудит качества RAG (QA): [`product_state/QA_ARCH_RAG_AUDIT.md`](product_state/QA_ARCH_RAG_AUDIT.md)

---

Reference: [`ENGINEERING_PLAN.md`](ENGINEERING_PLAN.md) §5 · `.cursorrules` (PROJECT MEMORY)
