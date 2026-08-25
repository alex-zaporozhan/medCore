# ARTIFACT_MAP — индекс слоя W

> **Версия:** 2026-04-02  
> **Назначение:** одна страница: что в `docs/artifacts/` и зачем. История волн удалена из репозитория как шум для RAG — см. git.

---

## Уровни (легенда)

| Код | Значение |
|-----|----------|
| **S** | Состояние продукта для AI — **`docs/product_state/`** (не дублировать здесь) |
| **P** | Норма процесса — **`docs/ROLE_*.md`**, паспорта в корне `docs/` |
| **W** | Эта папка: рабочий корпус, планы, маршруты |
| **H** | История — только **git** |

---

## Канон W (приоритет для «как устроен продукт»)

| ID | Файл | Зачем |
|----|------|--------|
| **W-A1** | [SAAS_ARCHITECTURE_SPINE_2026.md](./SAAS_ARCHITECTURE_SPINE_2026.md) | Архитектурный каркас |
| **W-P1** | [PRODUCT_OPERATING_CORPUS_2026.md](./PRODUCT_OPERATING_CORPUS_2026.md) | Продукт и фазы |
| **W-B1** | [BUSINESS_ROUTES.md](./BUSINESS_ROUTES.md) | API и SPA |
| **W-B2** | [BUSINESS_LOGIC.md](./BUSINESS_LOGIC.md) | Правила для @DEV |
| **W-N1** | [SME_BOX_NFR_CHECKLIST.md](./SME_BOX_NFR_CHECKLIST.md) | NFR коробки |
| **W-M1** | [METRICS_REGISTRY.md](./METRICS_REGISTRY.md) | M-XX |
| **W-L1** | [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | Текущий фокус |
| **W-M2** | [MARKET_AUDIT.md](./MARKET_AUDIT.md) | Рынок (@BIZ) |

---

## Вне `artifacts/`

| ID | Путь | Зачем |
|----|------|--------|
| **P-01** | `docs/ENGINEERING_PLAN.md` | Процесс ролей |
| **P-02** | `docs/product_state/README.md` | Слой S, allowlist RAG |
| **P-03** | `.cursorrules` | Законы репозитория |
| **P-04** | `docs/NONFUNCTIONAL_SCORECARD.md` | Enterprise NFR |
| **P-05** | `docs/DOC_TOPOLOGY.md` | Карта подпапок `docs/` (P/S/W, RAG-приоритет) |
| **P-06** | `docs/DEVELOPMENT_PLAN.md` | Указатель → `artifacts/DEVELOPMENT_PLAN.md` |
| **P-07** | `docs/RAG_CANON.md` | Порядок источников для AI, STUB, дубли |
| **P-08** | `docs/README.md` | Вход в документацию репозитория |

---

## Именование новых файлов

- Предпочтительно: расширять **SAAS_ARCHITECTURE_SPINE_2026.md** или **PRODUCT_OPERATING_CORPUS_2026.md**.  
- Допустимо: один файл **`ARCH_MODULE_<TOPIC>_2026.md`** на изолированную тему.  
- Не возвращать: сетки `ARCH_DEV_*`, `*_TASKS`, `DEV_PROMPTS_*` без явной задачи @LEAD.

---

## Волна A — эстетика / EN chrome (2026-08-23)

| ID | Файл | Зачем |
|----|------|-------|
| **W-FE1** | [FRONTEND_AESTHETICS_AUDIT_2026-08-23.md](./FRONTEND_AESTHETICS_AUDIT_2026-08-23.md) | Анамнез + диагноз по URL владельца |
| **W-FE2** | [FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md](./FRONTEND_COSMETIC_ORDER_TZ_2026-08-23.md) | ТЗ лечения (без кода) |
| **W-FE3** | [QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md](./QUEUE_FRONTEND_COSMETIC_ORDER_2026-08-23.md) | Промпты Q0–Q13 для Cursor queue |
| **W-FE4** | [FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md](./FRONTEND_COSMETIC_ORDER_NEXT_2026-08-23.md) | Вне волны A: A2 C1, seed, AI tasks, grep-гейт, concept лендинга |

Код волны **не писать**, пока владелец не вставит очередь. ТЗ/очередь — **rev 3** (D4 = text+blur не `type=time`; полные карты i18n; JSON один писатель; 6 вкладок nowrap). Канон i18n: [ADMIN_I18N_EN_ROADMAP.md](./ADMIN_I18N_EN_ROADMAP.md).

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-08-23 | Волна A rev 3: D4 typing, полные i18n-карты, JSON-гонки, аудит §10 (без кода) |
| 2026-08-23 | Волна A rev 2: ревью гонок/контрактов + NEXT-промпты (без кода) |
| 2026-04-02 | Консолидация: spine + corpus; удалены архив, 85 plus, промпты и дубли |
| 2026-03-24 | Первая версия карты (до зачистки) |
