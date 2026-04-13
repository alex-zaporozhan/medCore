# Commerce — bounded context (Фаза 4, опционально)

> **Статус:** границы bounded context зафиксированы в ADR-013; миграции `commerce_*` и админский API уже в коде (см. ниже). **План магазина + витрина PWA:** [COMMERCE_STORE_ARCHITECTURE_PLAN.md](./COMMERCE_STORE_ARCHITECTURE_PLAN.md).  
> **ADR:** [ADR-013](../../adr/ADR-013-commerce-store-bounded-context-scope.md) (Proposed; см. дополнение 2026-04-11 про публичную витрину).  
> **Entitlement (каталог):** `commerce.store_network` — строка в `platform_catalog_options` с **`is_active = false`** до продуктового go; продажа и гейты API — только после записи ARCH+LEAD.

## Границы

- **Входит:** номенклатура, единицы измерения, склады/точки продаж внутри `clinic_id`, документы движения (приход/расход/перемещение), заказы и продажи **в рамках организации и точки**, read-models / витрины для сети клиник.
- **Не смешивать:** транзакционные строки заказов разных `clinic_id` без явного RBAC и аудита; «общая куча» сетевых продаж — только через агрегаты.
- **Связь с импортом:** выгрузки 1С и номенклатура — профиль enterprise-конвейера [data_migration_import_connectors.md](../modules/data_migration_import_connectors.md) + МП §25.

## Резерв имён (Python / API — черновик)

| Область | Префикс / пакет | Примечание |
|---------|-----------------|------------|
| Роутеры админки | `admin_commerce_*` | Подключать с `require_entitlement("commerce.store_network")` |
| Публичные маршруты | `public_commerce` — `GET /api/v1/public/clinics/{clinic_id}/commerce/vitrine` | Read-only витрина (MVP): см. ADR-013 дополнение и [COMMERCE_STORE_ARCHITECTURE_PLAN.md](./COMMERCE_STORE_ARCHITECTURE_PLAN.md) §6 бэклог по rate limit / OpenAPI |
| Сервисы приложения | `src/application/services/commerce_*` | |
| Сущности ORM | `src/domain/entities/commerce_*` | Не создавать таблицы до ADR + go |
| Репозитории | `*_commerce_*_repo_impl.py` | |

## Резерв имён таблиц БД (не создавать до go)

Префикс таблиц: **`commerce_`** (снижает риск коллизий с существующими `erp_*`, `financial_*`).

| Таблица (план) | Назначение |
|----------------|------------|
| `commerce_nomenclature_items` | Справочник SKU / услуг как товарных позиций |
| `commerce_uom` | Единицы измерения |
| `commerce_stock_locations` | Склад или точка внутри `clinic_id` |
| `commerce_stock_balances` | Остатки (по location + SKU) |
| `commerce_documents` | Шапка документа движения |
| `commerce_document_lines` | Строки документа |
| `commerce_sales_orders` | Заказ (опционально отдельно от «документов» — уточнить в ADR перед миграцией) |
| `commerce_import_jobs` | Аудит успешных CSV-импортов + идемпотентность `(organization_id, idempotency_key)` (4-F5) |

Точный ER и разделение «заказ vs расходная накладная» — в amendment ADR-013 при первом PR схемы.

## Ворота

1. Явная запись **ARCH + LEAD** (или тикет со ссылкой на ADR-013) перед **первой** миграцией, создающей таблицы `commerce_*`.
2. Включить **`is_active`** для опции каталога и продавать SKU только после SEC + продуктового скоупа.
3. Сетевые своды — только read-models; см. МП §26 и [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).

## Связанные документы

- [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md) — будущая строка `admin_commerce_*`.
- [05_data_migrations_multitenancy.md](../05_data_migrations_multitenancy.md) — мультитенантность миграций.

**Факт кода:** миграции `20260417`…`20260419_phase4_commerce_movement_documents` и **`20260420_commerce_goods_transfer`** — `commerce_documents`, `commerce_document_lines` (виды `goods_in` / `goods_out` / **`goods_transfer`**; для перемещения колонка **`to_stock_location_id`**, CHECK: для in/out поле NULL, для transfer NOT NULL и ≠ `stock_location_id`), плюс остатки; роутер `admin_commerce.py` — overview, CRUD точек и номенклатуры, остатки, **движения:** `GET|POST …/commerce/movements`, `GET …/movements/{id}` (проводка в `commerce_stock_balances`: transfer — минус с источника, плюс в назначение; расход/transfer при нехватке → 409). **Витрина сети (4-F3):** `admin_commerce_network.py` — `GET …/admin/organization/commerce/network-overview`. **Импорт CSV (4-F4 / 4-F4b / 4-F5):** номенклатура — `GET|POST …/commerce/nomenclature/import-spec|import-csv` (`commerce_nomenclature_csv_v1`); остатки на точке — `GET|POST …/stock-locations/{id}/balances/import-spec|import-csv` (`commerce_stock_balances_csv_v1`, `sku` + `quantity`); журнал и идемпотентность — таблица `commerce_import_jobs`, `GET …/commerce/import-jobs`, заголовок `Idempotency-Key` на POST импорта. Общий лимит строк — `COMMERCE_CSV_IMPORT_MAX_ROWS`. Сущности `CommerceDocument`, `CommerceDocumentLine`, `CommerceStockBalance`, `CommerceImportJob`, … Тяжёлые enterprise-пайплайны — см. ADR-010 / `data_migration_import_connectors.md`.

### Пациентская витрина (PWA), 2026-04-11

- **Миграция:** `20260429_clinic_patient_storefront_flags` — колонки `patient_store_visible`, `patient_store_title`, `patient_store_subtitle` на `clinics`.
- **Публичный API:** `src/api/v1/routers/public_commerce.py` — витрина номенклатуры при включённом флаге.
- **Фронт:** `StorePage`, навигация «Магазин» в `AppLayout` при `patient_store_visible`; настройка и превью карточек в `AdminCommercePage`.
- **Тесты:** `tests/api/test_public_commerce_vitrine.py`.

**Версия:** 2026-04-06 — черновик + первый вертикальный срез таблиц/API; 2026-04-11 — витрина PWA и ссылка на план.
