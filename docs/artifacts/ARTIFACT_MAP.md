# ARTIFACT_MAP — карта артефактов (что открывать и зачем)

> **Назначение:** одна страница ориентира: **номер / уровень / имя файла / роль**. Ничего не удаляет и не заменяет — только навигация.  
> **Обновление:** при добавлении нового канонического документа — строка в таблице «Канон» + при необходимости ссылка из этого файла.

---

## 1. Уровни (легенда)

| Код | Значение | Кто читает |
|-----|----------|------------|
| **S** | Source of truth (канон) | Все, в первую очередь |
| **M** | Мастер-план / сквозная трассировка | LEAD, ARCH, продакт |
| **A** | Атлас / индекс для ИИ и людей | ARCH, DEV при смене модуля |
| **D** | Playbook исполнения | DEV, QA |
| **N** | NFR / качество / релиз | OPS, QA_ARCH |
| **H** | История / архив / не канон | Справка, сравнение, не для поставки |

---

## 2. Канон (открывать в первую очередь)

| ID | Уровень | Файл | Зачем |
|----|---------|------|-------|
| **S-00** | S | [README.md](./README.md) | Индекс актуальных ссылок |
| **S-01** | M | [MASTER_PRODUCT_ROADMAP_2026.md](./MASTER_PRODUCT_ROADMAP_2026.md) | Фазы, Box vs Enterprise, QA_ARCH |
| **S-02** | M | [PRODUCT_IA_RBAC_NAVIGATION_2026.md](./PRODUCT_IA_RBAC_NAVIGATION_2026.md) | Меню, роли, роуты |
| **S-03** | M | [PRODUCT_PASSPORT_UX_DESIGN_BACKEND_2026.md](./PRODUCT_PASSPORT_UX_DESIGN_BACKEND_2026.md) | UX, уведомления, омниканал, Kanban |
| **S-04** | N | [SME_BOX_NFR_CHECKLIST.md](./SME_BOX_NFR_CHECKLIST.md) | Минимум NFR для коробки |
| **S-05** | A | [ARCHITECTURE_ATLAS_2026.md](./ARCHITECTURE_ATLAS_2026.md) | Модули, границы, диаграммы |
| **S-06** | D | [DEV_EXECUTION_PLAYBOOK_2026.md](./DEV_EXECUTION_PLAYBOOK_2026.md) | Как брать работу, DoD, порядок чтения |
| **S-07** | M | [TZ_COVERAGE_MATRIX_2026.md](./TZ_COVERAGE_MATRIX_2026.md) | Покрытие ТЗ ↔ фазы, пробелы |

### Архитектура @ARCH (фазы и сквозные)

| ID | Файл | Зачем |
|----|------|-------|
| **A-00** | [ARCH_INDEX_PHASES_2026.md](./ARCH_INDEX_PHASES_2026.md) | Оглавление P0–P7 |
| **A-01** | [ARCH_CROSS_CUTTING_UI_I18N_2026.md](./ARCH_CROSS_CUTTING_UI_I18N_2026.md) | Модалки по центру, RU-only UI |
| **A-02** | [ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md](./ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md) | БД, бэкапы, мультитенантность |
| **P-00** … **P-07** | `ARCH_PHASE_0*_…_2026.md` | Одна карточка на фазу (см. A-00) |

---

## 3. Проект в целом (вне `artifacts/`)

| ID | Файл | Зачем |
|----|------|-------|
| **P-01** | `docs/NONFUNCTIONAL_SCORECARD.md` | Живой Enterprise scorecard |
| **P-02** | `docs/ENGINEERING_PLAN.md` | Процесс ролей и quality gate |
| **P-03** | `.cursorrules.md` | Правила репозитория для ИИ и людей |
| **P-04** | `docs/development/TEST_DATABASE.md` | Одна схема для pytest = `alembic upgrade head` (не `create_all`) |
| **P-05** | `docs/archive/README.md` | Короткий индекс; канон vNext — в корне `docs/artifacts/` (`DEV_*`, `ARCH_DEV_COVERAGE_NEXT`) |

---

## 4. Полка **85 plus** (8.5+, запланировано)

| Путь | Статус |
|------|--------|
| `docs/artifacts/85 plus/` | **M / N** — дорожная карта и трекер 8.5+, REDISIGN, PROJECT_INTERNALS; **не** архив «мёртвых» документов; канон файлов в этой папке — см. [`85 plus/README.md`](./85%20plus/README.md) |

Канон программы 8.5+ — только файлы в этой папке (дубликатов в корне `docs/artifacts/` нет).

---

## 5. Архив и `_outdated`

| Путь | Статус |
|------|--------|
| `docs/artifacts/archive/` | **H** — справочные копии; не канон без пометки |
| `docs/artifacts/archive/_outdated/` | **H** — копии; папка в **`.cursorignore`** |

### Про дубликаты и Cursor

- Файлы в **`docs/artifacts/archive/_outdated/`** индексатор Cursor **не подмешивает** в контекст — для ИИ это **не дубликат внимания**.
- Если **тот же текст** всё ещё лежит **вне** `_outdated` (например в корне `docs/artifacts/`), то для людей и git **две копии на диске** — это уже дубликат; канон см. таблицу «Канон» выше.
- Программа **QA_ARCH 8.5+** перенесена в **`85 plus/`** (не в `archive/`).

---

## 6. Именование новых файлов (рекомендация)

- Канон: **`ИМЯ_2026.md`** или **`ИМЯ_ATLAS_2026.md`**, без произвольных суффиксов.
- Модульные спеки: **`ARCH_MODULE_<NAME>_2026.md`** или существующие `ARCH_DEV_*` / `ARCH_*` — не переименовывать массово; новые — по шаблону из **S-06**.

---

## 7. История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | Первая версия карты |
| 2026-03-25 | Полка `85 plus/`; vNext-артефакты в корне `artifacts/`; `docs/archive/README` — индекс |
