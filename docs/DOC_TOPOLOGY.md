# DOC_TOPOLOGY — карта папок под `docs/`

> **Версия:** 2026-04-09 (фазы 6–8: чеклисты в `frontend/PHASE_*.md`; фаза 3 без изменения смысла)  
> **Назначение:** куда класть файлы и что индексировать в RAG первым.  
> **Порядок истины при конфликте:** код и тесты → **`docs/product_state/`** (S) → остальной **`docs/`** (P).

---

## Слои (фактическое использование)

| Слой | Где | Смысл |
|------|-----|--------|
| **S** | `docs/product_state/` | Снимки «что есть в коде»: паспорта backend/frontend, архитектура, структура, коммерческая интерпретация, карта `.md`, baseline RBAC. Вход: [`product_state/INDEX.md`](product_state/INDEX.md). |
| **P** | Корень `docs/*.md` | Процесс: роли (`ROLE_*`), шаблоны (`TEMPLATE_*`), протоколы LEAD, TPF, NFR, деплой-гайды. **Не** заменяют код как описание продукта. |
| **W** | `docs/artifacts/` | Отчёты QA, spine, планы волны; живой корпус процесса. **Не** слой S: при конфликте с кодом/`product_state/` — верить коду и S. Вход: [`artifacts/README.md`](artifacts/README.md). |
| **H** | Вне git / архивы | Каталоги из `.gitignore` (`docs_archive`, локальные черновики) — не коммитить; не опираться на них в RAG. |

**Не плодить второй слой S** вне `docs/product_state/` без решения @LEAD: длинные обзоры остаются в `docs/architecture/` как **P-уровень** с явной привязкой к коду в тексте.

---

## Подпапки и файлы первого уровня под `docs/`

| Путь | Содержимое | RAG-приоритет |
|------|------------|----------------|
| **`product_state/`** | Паспорта из кода, `generated/` (опционально, автоген), `baselines/` | **Высокий** |
| **`frontend/`** | Канон UI/архитектуры SPA, инженерные соглашения, критерии паспорта, **мастер-план фаз и чеклисты 6–8 (C4–D3):** [`frontend/MASTER_FRONTEND_EXECUTION_PLAN.md`](frontend/MASTER_FRONTEND_EXECUTION_PLAN.md), [`frontend/PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](frontend/PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md), [`frontend/PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](frontend/PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md), [`frontend/PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](frontend/PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md); также [`frontend/FRONTEND_ARCHITECTURE_CANON.md`](frontend/FRONTEND_ARCHITECTURE_CANON.md), [`frontend/FRONTEND_ENGINEERING_CONVENTIONS.md`](frontend/FRONTEND_ENGINEERING_CONVENTIONS.md), [`frontend/PAGE_PASSPORT_CRITERIA.md`](frontend/PAGE_PASSPORT_CRITERIA.md), [`frontend/UI_THEME.md`](frontend/UI_THEME.md) | **Высокий** (вопросы по экранам, стилю и приёмке) |
| **`frontend/pages/`** | Пер-страничные паспорта (RAG + приёмка); индекс покрытия — [`frontend/pages/README.md`](frontend/pages/README.md); карта дублей с рубрикой — [`frontend/RAG_FRONTEND_SOURCE_MAP.md`](frontend/RAG_FRONTEND_SOURCE_MAP.md) | **Высокий** (конкретный экран) |
| **`architecture/`** | Длинная архитектурная проза, планы @ARCH, модули backend/frontend/domains; оглавление — [`architecture/INDEX.md`](architecture/INDEX.md) | Средний / высокий по теме (после S) |
| **`design/`** | Дизайн 85+, токены, карта design→code — [`design/DESIGN_CODE_MAP.md`](design/DESIGN_CODE_MAP.md) | Средний (UI/визуал) |
| **`artifacts/`** | Слой W: QA, spine, метрики волны — [`artifacts/README.md`](artifacts/README.md) | Средний (процесс; не факты рантайма) |
| **`review/`** | Матрицы review, execution plans — вспомогательно для людей | Низкий / по задаче |
| **`operations/`** | Runbooks, DR, release, SLO | Средний (OPS) |
| **`adr/`** | ADR | Средний |
| Корень `docs/` | Роли, шаблоны, канон тестов, метрики, паспорта зрелости | Средний / по теме вопроса |

**Корень репозитория `documentation/`** — контур пользовательских и интеграторских материалов (см. [`DOCUMENTATION_POLICY.md`](../DOCUMENTATION_POLICY.md)); не дублировать тело инженерных паспортов там.

**Не ждать:** вложенного `docs/documentation/` как дубликата инженерного канона.

---

## Правила, чтобы не плодить шум

1. **Главный архитектурный снимок по продукту** — расширять [`product_state/ARCHITECTURE_FROM_CODE.md`](product_state/ARCHITECTURE_FROM_CODE.md) и паспорта, а не плодить второй «spine» в корне `docs/`.  
2. **Не подменять S слоем W** — не использовать `artifacts/` как единственный источник «что в проде»; факты — `product_state/` + код.  
3. Новые процедуры запуска/миграций — `docs/RUN_SERVICES.md`, `docs/MIGRATION_UPGRADE.md` или узкий ADR.  
4. **`docs/DEVELOPMENT_PLAN.md`** — если остаётся указателем, пусть указывает на **код** и **`product_state/INDEX.md`**, а не на несуществующие артефакты.

---

## Код и ссылки на документацию

- В **`src/`** и **`frontend/src/`** не размещать ссылки на файлы `*.md` (ни `documentation/…`, ни `docs/…`) — см. [`product_state/QA_ARCH_RAG_AUDIT.md`](product_state/QA_ARCH_RAG_AUDIT.md).  
- Политика репозитория: корневой **`DOCUMENTATION_POLICY.md`**.

---

## Опциональная реорганизация (`docs/roles/`, `docs/templates/`)

Перенос `ROLE_*` / `TEMPLATE_*` в подпапки остаётся **опциональным** (оценка труда — как в прежней версии §): ~0.5–1.5 дня с обновлением всех ссылок и `.cursorrules`. Для RAG достаточно явного allowlist в инструменте индексации.

---

Reference: [`RAG_CANON.md`](RAG_CANON.md) · [`product_state/README.md`](product_state/README.md) · [`ENGINEERING_PLAN.md`](ENGINEERING_PLAN.md) §5
