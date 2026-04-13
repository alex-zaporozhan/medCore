# Фаза 4 (опционально) — Commerce / магазин / 1С (optional_late_Commerce)

**Узел МП mermaid:** `optional_late_Commerce` (`Commerce_bounded_context`, `Store_sales_per_clinic`, `1C_compat_read_models`).  
**Связь МП:** §26, §4 ключ `commerce.store_network`, МП §15 (стрелка p3→p4 — приоритет, не обязательность).

## Архитектурный целевой образ

1. **Bounded context «Commerce»** — отдельный ADR или раздел домена **до первой миграции** магазина (МП §15b строка для фазы 4).
2. **Данные** — все операции с привязкой `organization_id` + `clinic_id` (или склад внутри точки); нет смешения заказов между клиниками без RBAC (МП §26).
3. **Сеть клиник** — своды только через витрины/read models, не через «общую кучу» транзакционных строк.
4. **1С** — целевая схема номенклатуры и документов движения; выгрузки через enterprise-конвейер §25 (МП §26 связь с импортом).
5. **UI** — нейтральная терминология (связь с §29).

## Ворота

- Явная запись **ARCH + LEAD** перед первой миграцией Commerce (МП §15b фаза 4).
- Entitlement `commerce.store_network` включается только при готовом продуктовом скоупе и SEC-обзоре.

## Порядок работ @DEV (высокоуровнево)

1. Заглушки интерфейсов и резерв имён модулей/таблиц в документации домена **до** массового рефакторинга ядра записи (МП §26).
2. После go — миграции и API в границах context; отчёты через агрегаты.

## Ссылки

- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) §6 (если есть про сервисы)
- МП [§26](../SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-26)
- [domains/commerce_bounded_context.md](../domains/commerce_bounded_context.md) — резерв имён таблиц и API
- [ADR-013](../../adr/ADR-013-commerce-store-bounded-context-scope.md) — bounded context (Proposed)

## Мини-план итераций @DEV

| Итерация | Содержание | Статус |
|----------|------------|--------|
| 4-F1–F2 | Точки, номенклатура, остатки, документы приход/расход/перемещение | сделано |
| 4-F3 | Read-model сети (`network-overview`) | сделано |
| 4-F4 | CSV номенклатуры (`commerce_nomenclature_csv_v1`) | сделано |
| 4-F4b | CSV остатков по точке (`commerce_stock_balances_csv_v1`) | сделано |
| 4-F5 | Таблица `commerce_import_jobs`, аудит успешных CSV-импортов, `Idempotency-Key`, `GET …/import-jobs` | сделано |
| 4-F5+ | Фоновая очередь, крупные файлы, запись failed-jobs без конфликта с `get_db` ([ADR-010](../../adr/ADR-010-external-crm-import-scope.md)) | бэклог |
| **4-F6** | **Пациентская витрина (PWA):** колонки `clinics.patient_store_*`, `GET …/public/clinics/{id}/commerce/vitrine`, страница `/app/store`, навигация и блок настроек в `/admin/commerce`; тесты `test_public_commerce_vitrine.py` | сделано (2026-04-11); план: [COMMERCE_STORE_ARCHITECTURE_PLAN.md](../domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md) |

## Статус @DEV (2026-04-06, доработка)

- **Документация:** [domains/commerce_bounded_context.md](../domains/commerce_bounded_context.md), [domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md](../domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md), [ADR-013](../../adr/ADR-013-commerce-store-bounded-context-scope.md) (Proposed + дополнение витрины); навигация INDEX / ENTITLEMENT_ROUTER / domain_layer.
- **Каталог платформы:** `20260416_phase4_commerce_catalog_placeholder` — **`commerce.store_network`**, `is_active = false` (публичный каталог не отдаёт неактивные опции).
- **Схема и API:** миграции `20260419_phase4_commerce_movement_documents` + `20260420_commerce_goods_transfer` — `commerce_stock_*`, `commerce_nomenclature_*`, `commerce_documents` (**`to_stock_location_id`** для `goods_transfer`: откуда = `stock_location_id`, куда = `to_stock_location_id`), `commerce_document_lines`; роутер [admin_commerce.py](../../../src/api/v1/routers/admin_commerce.py): overview, точки, номенклатура, остатки, **движения** `GET|POST …/commerce/movements`, `GET …/movements/{id}` (`doc_kind`: `goods_in` | `goods_out` | **`goods_transfer`**); RBAC `view_inventory` / `manage_inventory` + **ENT**; сервис [commerce_store_service.py](../../../src/application/services/commerce_store_service.py); **box** и SaaS: ключ в `BOX_BLOCKED_ENTITLEMENT_KEYS`.
- **Фронт:** `/admin/commerce` — сводка, точки, остатки, **таблица документов + форма проведения**, номенклатура; пункт сайдбара; в Box сегмент скрыт (`VITE_EDITION`).
- **Тесты:** [test_phase4_commerce.py](../../../tests/api/test_phase4_commerce.py); скрипт [check_admin_entitlement_routers.py](../../../scripts/check_admin_entitlement_routers.py).
- **4-F3 (read-model сети):** `GET /api/v1/admin/organization/commerce/network-overview` — по организации админа: все клиники с `organization_id`, агрегаты точек, номенклатуры и суммы остатков; роутер [admin_commerce_network.py](../../../src/api/v1/routers/admin_commerce_network.py); `get_commerce_network_overview` в [commerce_store_service.py](../../../src/application/services/commerce_store_service.py); UI блок «Сеть организации» на `/admin/commerce`.
- **4-F4 (импорт / 1С-friendly CSV):** профиль `commerce_nomenclature_csv_v1` — `GET …/commerce/nomenclature/import-spec`, `POST …/commerce/nomenclature/import-csv` (multipart, UTF-8); upsert по `sku` в рамках клиники; общий лимит строк — `COMMERCE_CSV_IMPORT_MAX_ROWS` в [commerce_store_service.py](../../../src/application/services/commerce_store_service.py); UI — загрузка CSV в разделе номенклатуры на `/admin/commerce`.
- **4-F4b (остатки по точке):** профиль `commerce_stock_balances_csv_v1` — `GET|POST …/stock-locations/{location_id}/balances/import-spec|import-csv`; колонки `sku`, `quantity`; сопоставление с номенклатурой клиники; UI — блок «Остатки по точке» на `/admin/commerce`.
- **4-F5 (импорт jobs + идемпотентность):** миграция `20260421_commerce_import_jobs` — `commerce_import_jobs` (уникальность `(organization_id, idempotency_key)`); при успешном импорте пишется строка аудита; заголовок **`Idempotency-Key`** на POST import-csv — повтор с тем же ключом и тем же профилем/областью возвращает сохранённый результат без повторной записи; конфликт профиля/точки → 409 `commerce_import_idempotency_scope_mismatch`; `GET …/commerce/import-jobs` — журнал по клинике; UI — карточка «Журнал импортов CSV». Неуспешные импорты в v1 не пишутся в jobs (избегаем лишнего `commit` до `HTTPException` в связке с `get_db`).
- **Дальше (4-F5+):** очередь/Celery, большие файлы, при необходимости — отдельная запись failed jobs (out-of-band commit или исключение `HTTPException` из общего `except` в `get_db`).

## QA_ARCH / долг (2026-04-06)

**Отчёт:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (секция **Фаза 4**).  
**Матрица эпиков:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — секция «Фаза 4», идентификаторы **4-F6…4-F11**.

Кратко:

- **Сделано в этом цикле:** восстановление после гонки идемпотентности (`IntegrityError` → `rollback` → replay committed job); UI передаёт `Idempotency-Key` на POST импорта; негативный тест 404 для «чужого» `clinic_id` в пути.
- **Открыто:** Accepted ADR-013 + запись ворот ARCH+LEAD; конвейер §25 / staging / очередь (**4-F5+**); метрики импорта; выравнивание effective-org с паттерном CRM import (**3-F3**); опционально негатив **403** для клиники другой организации.
