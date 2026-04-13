# Фаза 1b — коммерция и UX (Phase_1b_Commerce_UI)

**Узлы МП mermaid:** `Catalog_options_tariffs`, `Founder_console_dashboards_owners`, `Public_landing_signup`, `Payment_webhook_provision` (B4).  
**Связь МП:** §3–§8, §6, §10, §13.2, §15c, §16.6, ADR-011, **ADR-012** (refund/chargeback → org), [platform_subscription_billing.md](../modules/platform_subscription_billing.md).

## Архитектурный целевой образ

1. **Каталог** — опции и тарифы в БД; связь org↔entitlements как целевое состояние после оплаты (МП §3; фактическая запись — см. §6 «после paid»).
2. **Два контура webhook** — A (пациент→клиника) и B (подписка платформы): разные URL/префиксы и **разные секреты** (МП §6, U-006).
3. **Полный провижининг** — не только `Organization` + `Clinic`, но первый **Владелец/AdminUser**, приглашение, **`organization_entitlements`** из снимка тарифа (МП §2d п.8, §6).
4. **Жизненный цикл платежа B** — state machine: отмена, возврат, chargeback, согласованная с ручным reconcile (МП §6, §16.6 шаг 0).
5. **C2** — retry провижининга, DLQ, метрики «stuck paid», UI reconcile у Основателя (МП §6, §16.6 шаги 3–4); связь с outbox при multi-replica (§17.1).
6. **Публичный webhook B** — rate limit / WAF по политике SEC (МП §10); OpenAPI B после первого PR (МП §2d п.3).
7. **Лендинг и signup** — не считать готовыми без антиспама и наблюдаемости (МП §5 C3, §2c).
8. **Абонементные пресеты плана (QA_ARCH / Product):** Основатель задаёт **тариф как подписку** не только через «конструктор из опций» с ценой за каждую опцию (`platform_catalog_options.list_price_rub`), но и **цена пакета по периоду** — минимум **месяц** и **год** (два явных поля цены или эквивалент в БД), чтобы на лендинге/checkout был выбор «оплатить помесячно / на год вперёд» при **одном и том же** наборе entitlements (`plan_slug` + `option_keys`). Детали модели и связь с `tariff_snapshot` / провайдером — [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3; трекинг долга и **что вынесено в следующие эпики** (checkout, retry vs гейт, audit в БД, recurring/НДС, CRUD опций) — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1b-F4–F9**.

## Порядок работ @DEV (рекомендуемый)

### Backend — волна **ADR-012** (после spine 1b, до «полного» §16.6 и платного лендинга без ручного контроля)

Норматив: [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md); детали: [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §12.

1. Расширить обработку webhook B: `refunded` / статусы спора → **идемпотентный** доменный сервис **отзыва** entitlements из `tariff_snapshot` + явное состояние подписки/intent (**suspended** / **billing_revoked** — поля по миграции @ARCH).
2. Метрики и алерты: «активный доступ при refunded» → 0 после применения политики; тесты цепочки `succeeded` → провижининг → `refunded` → entitlements отозваны; повтор webhook без двойного эффекта.
3. Согласовать матрицу статусов YooKassa с SEC/Product; ручной reconcile в кабинете Основателя — только через доменный сервис + аудит (§25).

### Backend — базовый порядок 1b

1. Завершить **контур B** до критериев МП §16.6 (не заявлять «1b закрыта» на MVP spine — МП §2d).
2. Добавить **OpenAPI** (или эквивалент) для путей webhook B.
3. Расширить автотесты: идемпотентность + **согласованный список веток** провайдера (с SEC/Product).
4. Реализовать **очередь/retry** провижининга и учётную модель DLQ (согласовать с ADR-009 в тексте ADR-011 / модуле биллинга — МП §19 п.11).
5. Провижининг: создать цепочку **приглашения** Владельца (magic-link / invite token — МП §7.2 M2).

### Frontend / периметр

1. Маркетинговый периметр или секции SPA + SEO (МП §2 таблица «лендинг»).
2. Экраны Основателя: дашборды, список Владельцев, конструктор тарифов (МП §7–§8) — по эпикам и DESIGN SPEC при необходимости.
3. Страницы privacy/terms — плейсхолдеры до заполнения (МП §5); чеклист [PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md](../PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md).

### Параллельно (P0 Security)

См. [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) и МП §15a — не откладывать до «после 1b».

## DoD (МП §15b 1b) — напоминание

- A и B разведены в **коде и конфиге**.
- OpenAPI B.
- Автотесты **контура B** (не подменяются тестами только A).

## Бэклог усиления (после spine 1b / под нагрузкой)

Не входит в минимальный DoD **§15b 1b**; закрывать при росте RPS на admin API или по итогам профилирования.

1. **Проверка отзыва биллинга (ADR-012) на каждом запросе с admin JWT** сейчас бьёт в БД (`organization_has_platform_billing_revoked`). Усиления: кэшировать результат на время **одного HTTP-запроса** (контекстный кэш в middleware/dependency) или ввести **инвалидацию JWT** (например поле `access_token_version` / `session_version` на `AdminUser`, инкремент при отзыве биллинга) — см. напоминание «изменение модели JWT» в [DEV_EXECUTION_SEQUENCE.md](./DEV_EXECUTION_SEQUENCE.md) (когда просить @ARCH).
2. **Полная матрица «событие провайдера → обработчик»** для контура B — вести в [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §12.1 по мере согласования с SEC/Product (не дублировать расходящимися таблицами в других файлах).
3. **Алерты Prometheus** по метрикам отзыва и webhook B — в скоупе фазы **1d**, см. [05_PHASE_1D_OBSERVABILITY.md](./05_PHASE_1D_OBSERVABILITY.md).

## Ссылки

- [ADR-011](../../adr/ADR-011-platform-subscription-webhook-provisioning.md)
- [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md)
- [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md) (контур A — отдельная линия)
- [API_VERSIONING_POLICY.md](../API_VERSIONING_POLICY.md) §3 (версии в пути при необходимости)

### Связка с Phase 1c (не потерять при коммерции и UI ошибок)

Единый регистр стабильных машинных `code` в JSON (в т.ч. после гейтов entitlements и «box») согласовать с SEC/Product и выровнять с дисциплиной каталога ошибок — [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) B2, [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q2**, [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) §28.

## Статус @DEV (фиксация прогресса)

- **2026-04-05:** OpenAPI для webhook B; таблица `organization_entitlements` + запись из `tariff_snapshot` (ключи `keys` / `entitlement_keys`, всегда включается `core.base`); первый `AdminUser` с ролью `owner` + хеш приглашения; `POST /public/platform/owner-invite/accept`; `POST /platform/internal/.../owner-invite-token` для выпуска токена Основателем (до email-автоматизации).
- **2026-04-05 (дозакрытие 1b spine):** каталог в БД + `GET /public/platform/catalog/plans|options`; `plan_slug` в снимке тарифа мержится с ключами из `platform_catalog_plans`; retry провижининга + DLQ-поля на `platform_signup_intents`, Celery beat `platform_billing.retry_due_provisions`; `GET/POST` reconcile у Основателя (`/platform/internal/provision-queue`, `.../retry-provision`); per-IP rate limit на webhook B (конфиг, в `TESTING` выключен); ветки YooKassa canceled/refunded в `apply_platform_yookassa_notification`; фронт: `/legal/privacy`, `/legal/terms`, `/platform/provision-queue`, лендинг — футер + блок тарифов из публичного API. **Вне 1b spine / позже:** полная матрица chargeback/edge YooKassa, WAF на периметре, антиспам signup, email-автоматизация приглашения владельца.
- **2026-04-05 (@QA_ARCH hardening):** `retry-provision` не поднимает неоплаченный intent (409, см. envelope `code` в `main.py`); при коллизии email владельца с существующим `AdminUser` провижининг падает в `provision_failed` (без «тихого» active); `/provision-queue` операционные статусы включая `suspended` после ADR-012 (см. @DEV); при `refunded` от YooKassa — идемпотентный отзыв entitlements (не только лог); UI основателя: маскирование токена, разбор ответа API с полем `code`, 503/409.
- **2026-04-05 (@QA_ARCH ADR-012):** после отзыва биллинга проверка не только на `POST /admin/auth/login`, но и на каждом запросе с admin JWT (`get_current_admin`, SSE-вариант, оба `get_current_admin_optional`, см. `platform_billing_access.organization_has_platform_billing_revoked` + `ADMIN_ORG_PLATFORM_BILLING_REVOKED` в `user_messages`); тест: существующий токен после refund не проходит `GET /admin/auth/session`.
- **2026-04-05 (@LEAD):** принят **[ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md)** — политика refund/chargeback и org после «денег назад»; реализация базового пути YooKassa `refunded` — см. строку @DEV ниже и `platform_subscription_billing.md` §12.
- **2026-04-05 (@DEV, ADR-012 в коде):** webhook B при `refunded` вызывает идемпотентный `apply_platform_billing_revocation_after_refund` (`platform_billing_service.py`): удаление entitlements с `source` в `tariff_snapshot` / `billing_revocation`, маркер `saas.billing_revoked`, `intent.status=suspended`, колонка `billing_revoked_at` (миграция `20260410_phase1b_billing_revocation`); метрика `platform_billing_billing_revocation_total`; `admin_login` — 403 для владельца org с таким intent; очередь Основателя включает `suspended` и поле `billing_revoked_at` в DTO; автотесты цепочки succeeded→refund и двойного webhook. **Вне spine:** полная матрица chargeback, WAF, антиспам signup, email invite.
