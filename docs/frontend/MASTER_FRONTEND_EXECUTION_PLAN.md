# Мастер-план: фронтенд, паспорта экранов и смежная документация

> **Версия:** 2026-04-09 (артефакты закрытия фаз 6–8 — три файла `PHASE_*` в этом каталоге; § «Глубина паспортов» без изменений смысла)  
> **Аудитория:** лид / @QA_ARCH — **последовательная** постановка задач агенту (одна фаза за раз).  
> **Назначение:** единая дорожная карта от «канон и RAG» до приёмки; без смешивания эпиков в одном чате без явной команды.

## Зачем этот файл

Исходная мастер-задача охватывает **несколько несовместимых режимов**: только markdown-паспорта без кода, глобальную реструктуру `docs/`, живой прогон UI с правками в `frontend/src/` и `src/`, копирайт и «покупательскую» приёмку. Этот план **раскладывает** работу на фазы; исполнитель на каждой фазе получает **одну** директиву и явные критерии готовности.

**Точка входа по критериям:** [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md).

---

## Скрипт паспортов SPA (обязательный якорь)

**Файл:** `scripts/gen_frontend_page_passport_stubs.py`  
**Корень команд:** из **корня репозитория** (`dental_booking/`).

| Команда | Когда запускать | Ожидание |
|--------|------------------|----------|
| **`verify`** | Перед стартом фазы с паспортами; **после каждых 5** шагов runbook 1–71; после правок `App.tsx` / `routePaths.ts`; в конце сессии агента по паспортам; **гейт перед PR**, если трогали маршруты или каталог `docs/frontend/pages/` | **exit 0**; иначе — починить пропущенные slug или восстановить файлы |
| **`generate`** | После **добавления** нового маршрута/экрана в коде: создаёт недостающие `docs/frontend/pages/<slug>.md` | Затем обновить матрицу в [`pages/README.md`](./pages/README.md), затем снова **`verify`** |
| **`print-matrix`** | Нужно **перегенерировать строки** таблицы Path → файл для `README.md` (массовое изменение списка slug) | Вставить вывод в README вручную, затем **`verify`** |
| **`migrate-placeholders`** | Разовая миграция старых текстов заглушек в `.md` (по указанию лида) | После — **`verify`** |

**Не путать:** `verify` **не** заменяет `npm run build` и **не** проверяет качество текста паспортов — только соответствие **множества маршрутов из кода** множеству файлов в `docs/frontend/pages/`.

**Связанный регламент:** [`FRONTEND_ENGINEERING_CONVENTIONS.md`](./FRONTEND_ENGINEERING_CONVENTIONS.md) §4 (чеклист при смене маршрута).

---

## Порядок фаз (эпики для агента)

Выполнять **по номеру**. Переход к следующей фазе — только после критериев «готово» или явного waiver лида.

| Фаза | Эпик | Суть работы | Основные артефакты / runbook | Критерий готовности (минимум) |
|------|------|-------------|--------------------------------|-------------------------------|
| **0** | Предпроверка и синхронизация с кодом | Убедиться, что инвентарь экранов не расходится с репозиторием | `python scripts/gen_frontend_page_passport_stubs.py verify` | `verify` → exit 0 |
| **1** | Канон фронта и дизайна **до** массового обхода страниц | Усилить «центральный компас»: архитектура SPA, токены, карта design→code, рубрика Enterprise | [`FRONTEND_ARCHITECTURE_CANON.md`](./FRONTEND_ARCHITECTURE_CANON.md), [`UI_THEME.md`](./UI_THEME.md), [`../design/DESIGN_CODE_MAP.md`](../design/DESIGN_CODE_MAP.md), [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) | Нет противоречий «где править тему / drawer / токены»; рубрика не пустая-заглушка **или** заведён тикет на наполнение |
| **2** | Паспорта экранов **v2** (документация по коду, без правок приложения) | Пошаговый проход 1–71; ось H, API из хуков, RBAC, gap scan | [`pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`](./pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md), [`pages/V2_ZONE_TRACKER.md`](./pages/V2_ZONE_TRACKER.md), [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md) | Зоны в трекере закрыты по правилам runbook; **после каждых 5 шагов и в конце** — `verify` |
| **3** | Глобальная документация репозитория и RAG (не только фронт) | `docs/architecture`, дедуп, навигация для людей и индексации | [`../RAG_CANON.md`](../RAG_CANON.md), [`../DOC_TOPOLOGY.md`](../DOC_TOPOLOGY.md), [`DOCUMENTATION_POLICY.md`](../../DOCUMENTATION_POLICY.md) | Согласованные входы; нет «фронт в трёх местах» без перекрёстных ссылок (ось **A1–A3** в выжимке) |
| **4** | Функциональный аудит UI + **допустимы правки кода** | Живой прогон: пустые селекты, мёртвые кнопки, связка с API; точечно `frontend/src/`, при необходимости `src/` | Отдельная постановка от лида (не runbook паспортов); фиксировать находки также в паспортах как **gap→resolved** по мере фикса | Критерии **C1–C2** из выжимки; после смены маршрутов — `generate` + **`verify`** |
| **5** | Копирайт и единый тон | Политика RU, вычистка «следов ИИ», согласованность подписей | [`../COPY_STYLE_POLICY_RU.md`](../COPY_STYLE_POLICY_RU.md) | **C3**; выборочный grep по `frontend/src` по шаблонам от лида |
| **6** | Визуальная целостность и премиум-слой | Браузер / скрин-регрессия по решению команды; выравнивание с дизайн-слоем 85+ где принято | [`../design/`](../design/), техпаспорт UI, **[`PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](./PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md)** | **C4**; ворота + пилоты из чеклиста; ручной проход зафиксирован |
| **7** | Сквозные сценарии PWA / публичная витрина | Цены, врачи, админка → публичный профиль и т.д. | Паспорта `app-*`, `public-doctor-profile`, **[`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md)** | **C5**; матрица сценарий / статус / gap обновлена |
| **8** | Приёмка «покупатель / техлид» | Несколько итераций рубрики, безопасность периметра по регламентам проекта | **[`PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](./PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md)** + **D1–D3** | Чеклист закрыт; **подпись лида** вне markdown или в тикете |

## Глубина паспортов: фаза 2 и «технредактор по API»

- **Фаза 2 — минимум по этому плану:** паспорт соответствует [`pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`](./pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md) §1 (метаданные, назначение, хуки и типовые пути из кода страницы, RBAC, ось H, target/as-built, тесты, gap scan). Якоря: [`pages/V2_ZONE_TRACKER.md`](./pages/V2_ZONE_TRACKER.md), `python scripts/gen_frontend_page_passport_stubs.py verify`. Этого **достаточно**, чтобы закрыть фазу 2 по таблице выше.
- **Полный построчный аудит** в стиле технредактора («каждая строка API в паспорте сверена с контрактом бэкенда и всеми ветками UI» по всем slug) **не выделен отдельной фазой 9**: он перекрывается **фазой 4** (живой прогон, критерии **C1–C2** в [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md) — фактически используемые эндпоинты и отсутствие мёртвых действий) и выборочной приёмкой лида по осям C и G в [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md).
- **Опционально:** лид может выдать под-задачу «deep review паспортов без правок кода» внутри **фазы 2** или как вступление к **фазе 4**; тогда в постановке явно задают выборку slug или полный набор и критерии «доказательной» сверки с API.

---

## Как выдавать задачу агенту (шаблон)

Скопируйте и заполните:

```text
Ты работаешь по фазе N из docs/frontend/MASTER_FRONTEND_EXECUTION_PLAN.md.
Соблюдай границы фазы: для фазы 2 — не менять frontend/src и src без отдельной команды.
В начале: python scripts/gen_frontend_page_passport_stubs.py verify
(для фазы 2 дополнительно вставь директиву из PAGE_PASSPORT_V2_AGENT_RUNBOOK.md с шагом N=…)
В конце сессии снова: verify и краткий отчёт: сделано / gap / следующий шаг.
```

---

## Артефакты закрытия фаз 6–8 (документация)

| Фаза | Файл |
|------|------|
| 6 | [`PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](./PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md) |
| 7 | [`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md) |
| 8 | [`PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](./PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md) |

---

## Связанные файлы (навигация)

| Файл | Роль |
|------|------|
| [`pages/README.md`](./pages/README.md) | Матрица Path → паспорт; скрипт в шапке |
| [`pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md`](./pages/PAGE_PASSPORT_V2_AGENT_RUNBOOK.md) | Детальная очередь шагов 1–71 и рецепт страницы |
| [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md) | Оси A–D мастер-задачи |
| [`FRONTEND_ENGINEERING_CONVENTIONS.md`](./FRONTEND_ENGINEERING_CONVENTIONS.md) | Слои SPA, чеклист PR, §4 маршруты + скрипт |
| `scripts/gen_frontend_page_passport_stubs.py` | `verify` / `generate` / `print-matrix` / `migrate-placeholders` |
| `scripts/enrich_page_passport_manifest.py` | Блок `AUTO_MANIFEST` во всех паспортах (статический анализ); см. [`PAGE_PASSPORT_AUTOMATION.md`](./PAGE_PASSPORT_AUTOMATION.md) |
| [`PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](./PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md) | **Лид:** что сделать руками по фазам 6–8 (таблица в начале файла) |

---

## Примечание @LEAD (фазы 6–8)

Автоматические ворота (сборка, `verify`, узкий vitest) фиксируются в [`PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md`](./PHASE_6_VISUAL_INTEGRITY_CHECKLIST.md) §«Журнал…». Осмотр UI в браузере, обновление статусов в [`PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md`](./PHASE_7_PWA_PUBLIC_SCENARIO_REPORT.md) и итоговая подпись по D1–D3 — в [`PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md`](./PHASE_8_LEAD_ACCEPTANCE_CHECKLIST.md) §«Пояснение…».

---

## Примечание @QA_ARCH

Фазы **2** и **4** сознательно разведены: смешение «только документы» и «чиним прод» в одном задании приводит к либо некачественным паспортам, либо к несанкционированным массовым правкам кода. Скрипт **`verify`** нужно держать **зелёным** после любых изменений, затрагивающих дерево маршрутов или каталог паспортов.
