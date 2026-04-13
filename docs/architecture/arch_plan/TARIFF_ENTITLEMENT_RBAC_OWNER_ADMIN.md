# Тариф (конструктор) ↔ entitlements ↔ RBAC ↔ админка Владельца

> **Роль:** мост между коммерческим «конструктором» (каталог опций и планов), договором с клиентом и исполняемой моделью в продукте.  
> **Связь:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) §3–§4, §12–§13, [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md), [ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md](../ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md), [LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md](../LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md), [00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md](00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md), [PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md](../../artifacts/PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md).

---

## 1. Три слоя ответственности (не смешивать)

| Слой | Вопрос | Источник истины | Ошибка, если перепутать |
|------|--------|-----------------|-------------------------|
| **Коммерция / договор** | За что платит клиника, что обещано в оферте | Каталог платформы + подписанный снимок (`tariff_snapshot` / план) | Спор «мы купили CRM» без строки в договоре |
| **Entitlement (SKU)** | Какие **функциональные пакеты** включены у `Organization` | Строки `organization_entitlements` (+ политика legacy: нет строк → не режем) | «Бесплатный» модуль при оплаченном только core |
| **RBAC** | **Кто** внутри организации может пользоваться включённым | Роли и permissions у `AdminUser` | Владелец без права ≠ «не куплено»; сотрудник с правом при отсутствии SKU = нарушение договора с платформой |

**Правило победителя:** *сначала entitlement (куплено ли), потом RBAC (кому разрешено).* API для платных модулей: `require_entitlement("<ключ>")` **и** при необходимости `require_permissions(...)`. UI: скрытие пункта меню по отсутствию ключа **дополняет**, но **не заменяет** проверку на бэкенде.

---

## 2. Единая цепочка «конструктор → исполнение»

1. **Каталог** (`platform_catalog_options`, `platform_catalog_plans`): каждая продаваемая опция имеет стабильный **`entitlement_key`** (канон — §4 / [ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md](../ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md)).
2. **Checkout / intent:** в `tariff_snapshot` фиксируются `plan_slug`, `billing_period`, при необходимости явный список ключей — см. [platform_subscription_billing.md](../modules/platform_subscription_billing.md).
3. **Провижининг после оплаты:** разрешение ключей → запись в `organization_entitlements` (всегда минимум `core.base`, если иное не оговорено продуктом).
4. **Сессия админки:** `GET /admin/auth/session` отдаёт `entitlement_enforced` (есть ли строки в `organization_entitlements`) и `entitlement_keys` для UI.
5. **Роутеры:** для опциональных модулей — `require_entitlement` по [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md); скрипт `scripts/check_admin_entitlement_routers.py` — регресс-ворота.

**PRINCIPLE:** любой новый платный модуль — одновременно: строка в каталоге, ключ в Phase0-таблице, гейт в API, строка в инвентаре, маппинг в `ADMIN_NAV_PATH_ENTITLEMENT_KEY` (фронт), негативный тест 403.

---

## 3. RBAC и «Владелец»

- **Владелец** (`owner`) — полномочия **управлять** организацией и персоналом; это **не** замена entitlement: владелец не «включает» CRM без SKU через UI, если продукт честный (исключение — только временные флаги суппорта/OPS с аудитом).
- Сотрудник с узкими правами не должен видеть разделы, которые запрещены RBAC, даже при наличии SKU; наоборот — при наличии SKU, но без права — раздел скрыт или только чтение по политике продукта.

---

## 4. Формулировка прайса (продукт и договор)

Опираться на [LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md](../LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md):

- **Три именованных тарифа** + модули; в публичном тексте называть не только цену, но **что входит в базу** (`core.base`) и что продаётся **отдельным ключом** (таблица соответствия «модуль → возможность в интерфейсе»).
- **Год / месяц:** явно фиксировать скидку и что происходит после окончания льготного периода (пилот).
- **Юридически:** формулировка «доступ к функциям X и Y в интерфейсе администратора в объёме, определённом выбранным планом и подключёнными опциями на дату оплаты» + ссылка на актуальный каталог или приложение к договору.

---

## 5. Текущие пробелы (честно)

| Зона | Риск | Направление закрытия |
|------|------|----------------------|
| Не все будущие модули с гейтом | Обход API без UI | Инвентарь + CI; периодический grep |
| ~~Статические `features.ts`~~ | Расхождение с SaaS | **Факт кода:** `resolveProductFeatures` / `useProductFeatures` (`frontend/src/config/features.ts`) при `entitlement_enforced`; legacy — всё включено. |
| ~~Только часть пунктов меню~~ | Путаница | Маппинг `ADMIN_NAV_PATH_ENTITLEMENT_KEY` покрывает все роутеры с `require_entitlement` в [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md); новые SKU — расширять синхронно. |
| Self-service **апгрейд оплаченной** существующей org | Двойной signup / новый intent | **Факт UI:** `/admin/subscription` — витрина `catalog_only` + карточка возможностей; кнопки публичного checkout не показываются. **Бэкенд:** отдельный `owner/checkout` или merge intent — эпик. |

---

## 6. Версия

- **2026-04-07** — первичная фиксация моста тариф ↔ RBAC ↔ админка Владельца (@LEAD / ARCH).
- **2026-04-07** — экран `/admin/subscription`, полоска владельца в `AdminLayout`, `resolveProductFeatures`, `PlatformPricingSection` `mode=catalog_only`.
