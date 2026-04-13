# ADR-013: Commerce / store / 1С-alignment — bounded context и scope

- **Статус:** Proposed  
- **Дата:** 2026-04-06  
- **Контекст:** Мастер-план SaaS [§26](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-26) и Фаза **4** ([09_PHASE_4_OPTIONAL_COMMERCE.md](../architecture/arch_plan/09_PHASE_4_OPTIONAL_COMMERCE.md)): опциональный модуль магазина и продаж по точкам сети, без блокировки ранних фаз. Риск — «тихие» таблицы вне согласованных границ и утечки данных между `clinic_id`.

## Решение

1. **Bounded context** с кодовым именем **Commerce** изолирован от ядра записи и ERP-отчётов: отдельные таблицы с префиксом `commerce_*`, отдельные сервисы и роутеры (см. [domains/commerce_bounded_context.md](../architecture/domains/commerce_bounded_context.md)).
2. **Мультитенантность:** каждая транзакционная строка несёт **`organization_id`** и **`clinic_id`** (или явный `stock_location_id`, однозначно принадлежащий клинике). Запросы без фильтра по орг/клинике из админских хендлеров — запрещены в дизайне; негативные тесты — в DoD реализации.
3. **Сеть клиник:** оперативные своды по продажам и остаткам для владельца сети — только через **read models / витрины** (материализованные представления, отдельные aggregate-таблицы или отчётный слой), а не смешение фактов продаж разных точек в одном запросе без RBAC.
4. **1С-совместимость:** целевой ориентир — справочник номенклатуры, единицы, склады, документы движения; обмен через тот же enterprise-конвейер, что и ADR-010 / §25 (отдельный профиль импорта). Детали форматов — отдельные задачи после v1 схемы.
5. **Продуктовый гейт:** entitlement **`commerce.store_network`** (МП §4); в каталоге платформы опция заведена с **`is_active = false`** до go; API и UI магазина не подключаются без `require_entitlement` и принятого [ENTITLEMENT_ROUTER_INVENTORY.md](../architecture/ENTITLEMENT_ROUTER_INVENTORY.md).

## Не входит в первый PR схемы (без отдельного решения)

- Полная бухгалтерская подсистема и НДС-разрез.
- Онлайн-касса фискализации (если потребуется — отдельный ADR и контур SEC).
- Замена существующих `financial_transaction` / кассы клиники; Commerce **дополняет** или интегрируется через явные границы, а не silent merge.

## Последствия

- Первый merge миграций `commerce_*` только после письменного **go ARCH + LEAD** и обновления статуса ADR (Accepted + ссылка на ревизию Alembic).
- Наблюдаемость: новые метрики — через реестр [07_metrics_observability.md](../architecture/07_metrics_observability.md).

## Связь

- ADR-010 (импорт), МП §25.3 (батчи), [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../architecture/TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).

---

## Дополнение 2026-04-11: публичная read-model «витрина» для PWA пациента

**Не отдельный ADR:** расширение read-path в том же bounded context **Commerce**.

1. **Данные клиники (не `commerce_*`):** флаги `patient_store_visible`, `patient_store_title`, `patient_store_subtitle` на `clinics` — переключатель и копирайт секции в приложении пациента; миграция `20260429_clinic_patient_storefront_flags`.
2. **Публичный HTTP:** `GET /api/v1/public/clinics/{clinic_id}/commerce/vitrine` — без аутентификации; если витрина выключена или клиника не найдена, ответ **200** с `enabled: false` и пустым `items` (не перечислять существование клиники через 404). Содержимое: активные строки `commerce_nomenclature_items` для того же `clinic_id`, лимит списка — по коду роутера.
3. **Объём MVP:** без цен, остатков, корзины и оплаты в этом эндпоинте; заказ/оплата — отдельные эпики и отдельный SEC-обзор при появлении денежного контура.
4. **Согласованность с п.3 исходного решения:** read-models для пациента не смешивают номенклатуру разных клиник; публичный маршрут не заменяет админский entitlement для записи.

Канонический план со ссылками на все связанные `.md`: [COMMERCE_STORE_ARCHITECTURE_PLAN.md](../architecture/domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md).
