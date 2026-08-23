# Модуль: биллинг подписки платформы (webhook, провижининг)

> **Статус:** реализован **MVP** контура B: `POST /api/v1/platform/billing/webhooks/yookassa`, таблицы `platform_signup_intents` / `platform_subscription_payments`, провижининг org+clinic при `succeeded` (идемпотентно). Reconcile UI и полный lifecycle — дальнейшие эпики.  
> **ADR:** [ADR-011](../../adr/ADR-011-platform-subscription-webhook-provisioning.md) (webhook, провижининг вперёд), [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md) (возврат / chargeback → org и entitlements)  
> **План:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) §6, §10, §16.6, §19

## 1. Назначение

Обеспечить приём оплаты **подписки SaaS** (Владелец бизнеса платит платформе) с **отдельным** webhook и данными от **пациентских** платежей (YooKassa и т.д. в существующем `payment_service`).

## 2. Границы и префиксы API

**Победитель решения (LEAD):** маршруты обработчика webhook платформы монтировать под префиксом, однозначно отличимым от публичного webhook пациента, например:

- `POST {api_v1_prefix}/platform/billing/webhooks/{provider}`  

где `provider` — `yookassa` | … Пациентский webhook остаётся на существующем пути (не смешивать в один обработчик без явного диспетчера по типу события **в начале** пайплайна).

## 3. Конфигурация и секреты

| Переменная (пример) | Смысл |
|---------------------|--------|
| `PLATFORM_BILLING_WEBHOOK_SECRET_*` | Секрет(ы) верификации подписи webhook **только** для контура B |
| `PLATFORM_BILLING_PROVIDER` | Активный провайдер для подписки (если один) |

Секреты **не** переиспользовать из конфига пациентских платежей. Production: secret manager (см. мастер-план §9).

### 3a. Время и UTC (PRINCIPLE)

Все поля времени платформенного контура (`expires_at` intent, `created_at`/`updated_at`, сроки в JSONB) хранить и сравнивать в **UTC** (`timestamptz` в PostgreSQL). Публичные API и UI обязаны документировать часовой пояс отображения; сервер не интерпретирует «локальное» время клиента без явного offset/IANA.

## 4. Модель данных (черновик схемы)

Имена таблиц — на усмотрение ARCH; логические сущности:

### 4.1 `platform_signup_intent` (или эквивалент)

- `id`, `created_at`, `expires_at`  
- Контактные поля (email, телефон — с учётом privacy §5 мастер-плана)  
- `tariff_snapshot` / ссылка на выбранные `entitlement` keys  
- `status`: `pending_payment` | `payment_initiated` | `paid` | `provisioning` | `active` | `failed` | `expired` | `manual_review`  
- `idempotency_key` (клиентский, если нужен)  
- Связь с будущей `organization_id` (nullable до провижининга)

### 4.2 `platform_subscription_payment` (или объединение с intent)

- `provider`, `provider_payment_id` — **UNIQUE** вместе  
- `amount`, `currency`, `status`  
- `signup_intent_id` FK  
- Сырой payload webhook (JSONB) для расследований — с политикой TTL/маскирования PII

### 4.3 Каталог: опции, пресеты планов и биллинг-периоды (QA_ARCH)

**Факт кода (2026-04-06):**

**Факт кода (каталог цен, 2026-08):** публичные list-цены планов — **USD-деноминированные** `$20 / $100 / $200` (миграция `20260433_catalog_usd_list_prices`). Имена колонок `price_*_rub` / `list_price_rub` сохранены (аддитивный контракт). Публичные DTO отдают `currency: "USD"`. Checkout отвечает `currency: "USD"` (каталог) и `charge_currency: "RUB"` (рельс YooKassa: то же число в RUB до появления USD/Stripe). Клиника-внутренние деньги (услуги, касса, зарплаты) остаются в ₽.

- Таблицы: `platform_catalog_options` (`list_price_rub`); `platform_catalog_plans` — `slug`, `option_keys`, **`price_monthly_rub`**, **`price_annual_rub`** (nullable), миграции `20260411_phase1b_catalog_plan_subscription_prices` и `20260433_catalog_usd_list_prices`.
- Публичное API: `GET /api/v1/public/platform/catalog/plans|options` (в планах — строки цен периодов).
- Основатель (JWT `platform_founder`): `GET` / `PUT /api/v1/platform/internal/catalog/plans` — список и upsert пресета; **`option_keys`** валидируются по строкам **`platform_catalog_options`**.
- **`resolve_entitlement_keys_for_intent`:** `plan_slug` в `tariff_snapshot` нормализуется к **lower** перед поиском плана.
- **Гейт оплаты (webhook YooKassa `succeeded`):** `src/application/services/platform_tariff_payment_gate.py`. Если в snapshot **есть** `billing_period` (`monthly` \| `annual`) **и** у активного плана задана цена выбранного периода — сумма из провайдера должна **совпасть** с каталогом; иначе intent **не** переводится в `paid`, `provision_last_error` = `tariff_gate:<код>`. Невалидный период / `billing_period` без `plan_slug` / неизвестный slug — блокируют авто-провижининг. Если **`billing_period` нет** в snapshot — гейт суммы **не** включается (legacy intent / тесты).
- **Аудит (минимум):** structured log `platform_catalog_plan_upsert` с `platform_founder_id` и `before`/`after`. Иммутабельная таблица в БД — бэклог **1b-F7** / **1a-F3** в [PHASE_FULL_CLOSURE_BACKLOG.md](../arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).

**1b-E5 (retry vs гейт, факт кода 2026-04-07):** `execute_platform_provision` перед созданием орг снова вызывает `evaluate_platform_payment_against_catalog` по последнему платежу YooKassa со статусом `succeeded` и `tariff_snapshot` intent. Ручной retry Основателя (`POST .../retry-provision`) **не** обходит гейт: при расхождении суммы с каталогом — `409` с кодом гейта (например `amount_mismatch_catalog`). Явного «override без аудита» в API нет.

**Целевое поведение (продукт, эпиками):** публичный **checkout** создаёт intent с `plan_slug` + `billing_period` и инициирует оплату на сумму из каталога; лендинг — выбор периода и CTA. Трекинг: **1b-F5–F8** в том же файле бэклога.

**Архитектурные инварианты:**

- После оплаты в `organization_entitlements` попадает **набор ключей** (из плана или снимка); период влияет на **деньги и продление**, а не на состав SKU, если иное явно не решено Product.
- В `tariff_snapshot` фиксировать **`billing_period`** и **`plan_slug`** для reconcile/refund/renewal (после checkout — основной путь).
- Публичный каталог отдаёт **видимые цены** по периодам в **USD** (`currency` в DTO); не подменять смысл «год = 12× месяц» без явной политики скидки. Рельс списания YooKassa в демо остаётся RUB с тем же числом (`charge_currency`).
- CRUD каталога — только `/platform/internal/*`; §25 / SEC: расширить до **таблицы audit в БД** (бэклог).

**Бэклог QA_ARCH (эпики):** см. [PHASE_FULL_CLOSURE_BACKLOG.md](../arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — **1b-F5** (checkout), **1b-F6** (retry vs гейт), **1b-F7** (audit БД), **1b-F8** (recurring / НДС), **1b-F9** (internal CRUD опций каталога).

**Open questions (Product + SEC + провайдер):** см. **1b-F8** в бэклоге полного закрытия фаз.

### 4.4 Синхронный провижининг vs outbox (ADR-009, МП §19 п.11)

**Факт кода (контур B, 2-E1):** при **`DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED=true`** (дефолт) после `succeeded` в **первой** транзакции webhook фиксируются `paid` и строка **`domain_outbox`** (`PlatformSignupProvision`); провижининг org/clinic выполняется в **`dispatch_domain_outbox_batch`** (после commit webhook и через Celery). Retry «зависших» paid intent по-прежнему — `platform_billing.retry_due_provisions`. При **`false`** — прежний двухфазный sync во второй транзакции HTTP-обработчика.

**Целевое согласование с ADR-009:** при **`replicas(API) ≥ 2`** на приёме публичного webhook B без sticky singleton — путь по **§17.1** ([API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md)) закрывается outbox-провижинингом (см. таблицу «Факт кода» там). Контур A (`PaymentSuccess`) — `domain_outbox` — [07_PHASE_2_RELIABILITY.md](../arch_plan/07_PHASE_2_RELIABILITY.md).

## 5. Машина состояний (сводка)

```
pending_payment → payment_initiated (создан платёж у провайдера)
                → paid (webhook success)
paid → provisioning → active (орг + владелец + entitlements готовы)
     → failed (ошибка провижининга) → retry → … → manual_review | active
```

- Переход в `active` **идемпотентен**: повторный `paid` webhook только обновляет метаданные платежа, не создаёт вторую организацию.  
- `expired`: по `expires_at` без оплаты — фоновая задача или lazy-проверка.

## 6. Обработка webhook (алгоритм)

1. Верификация подписи / IP allowlist (политика провайдера).  
2. Извлечь `provider_payment_id` и статус.  
3. Найти запись платежа или intent; если неизвестно — лог + 2xx при дубликате (чтобы провайдер не долбил) по политике idempotency.  
4. При `succeeded`: зафиксировать `paid`, поставить задачу **provision_organization** (синхронно только если допустимо по таймауту; иначе Celery + ADR-009 outbox для критичного шага).  
5. Любая необработанная ошибка после `paid` → инкремент retry, dead-letter после N попыток, алерт + запись для reconcile в UI Основателя.

**QA_ARCH (2026-04-07):** если провижининг падает с кодами гейта каталога / отсутствием succeeded-платежа (`PlatformProvisionRetryNotAllowed` из набора `PERMANENT_PROVISION_BLOCK_CODES`), в `provision_last_error` пишется префикс **`provision_blocked:`** без увеличения `provision_retry_count`; фоновый `run_due_platform_provisions` **не** выбирает такие intent (нет бессмысленного backoff). Метрика: `platform_provision_attempt_total{result="permanent_block"}`.

## 7. Reconcile (ручной контур)

В кабинете Основателя (мастер-план §7): UI **`/platform/provision-queue`** — очередь intent в состояниях `paid` / `provision_failed` / `dead_letter` / `suspended` (и застрявшие `pending_payment` с `tariff_gate:*`).

- **Retry:** `POST /api/v1/platform/internal/signup-intents/{intent_id}/retry-provision` — идемпотентный повтор провижининга (аудит `platform_signup_intent_retry_provision`).
- **Закрыть вручную (terminal):** `POST /api/v1/platform/internal/signup-intents/{intent_id}/manual-close` с опциональным `note` — для `provision_failed` / `dead_letter` после внешнего разбора (YooKassa, дубликат email владельца и т.д.); статус intent → **`reconcile_closed_manual`**; аудит `platform_signup_intent_manual_close`. Не заменяет refund/chargeback (ADR-012).

Операции должны быть **идемпотентны** на уровне домена (если org уже есть — не дублировать организацию).

## 8. Связь с entitlements

После успешного провижининга: заполнение `organization_entitlements` (или эквивалент) из `tariff_snapshot`; синхронизация с кэшем/сессией — вторична по отношению к БД.

## 9. Тесты (минимум, U-006 + контур B)

| Сценарий | Ожидание |
|----------|----------|
| Первый `succeeded` | Одна организация, статус `active` |
| Повторный `succeeded` с тем же `provider_payment_id` | Без второй организации |
| `succeeded` затем **refund** / chargeback (финальный проигрыш) | По [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md): отзыв paid-entitlements, явный статус подписки; **без** молчаливого `DELETE` org; идемпотентность повторного webhook |
| Ошибка БД в середине провижининга | Retry или `failed`, метрика, возможность reconcile |
| Неверная подпись webhook | 401/403, без смены состояния intent |

## 10. Наблюдаемость

Метрики (low-cardinality): `platform_billing_webhook_total{result}`, `platform_provision_attempt_total{result}`, `platform_provision_retry_scheduled_total`, **`platform_signup_intent_stuck`**, **`platform_signup_intent_dead_letter`** (gauges, обновляются при scrape `GET /metrics`, throttle `PLATFORM_BILLING_METRICS_DB_REFRESH_MIN_INTERVAL_SECONDS`), `platform_billing_gauge_refresh_failures_total`. Детальные логи — с `trace_id`, без сырых PAN/PII.

**Runbook (кратко, 1b-E4 / PRC-B4 C2):**

1. Алерт **PlatformSignupIntentProvisionBacklog** (`platform_signup_intent_stuck` > 0 дольше порога): открыть UI Основателя `/platform/provision-queue`, проверить `provision_last_error`, при необходимости **Retry**; убедиться, что Celery выполняет `platform_billing.retry_due_provisions`.
2. Алерт **PlatformSignupIntentDeadLetter**: только ручной разбор; проверить логи провижининга, целостность платежа в YooKassa, конфликт email владельца; не снимать DLQ без аудита. Подробный сценарий: [PLATFORM_BILLING_PROVISION_RECONCILE.md](../../operations/PLATFORM_BILLING_PROVISION_RECONCILE.md).
3. Пики **platform_billing_webhook_total{result=processing_error}**: см. существующий алерт в `deploy/prometheus/dental_booking_alerts.yml`.
4. **Outbox (§19 п.11, PRC-E3):** алерты **DomainOutboxOldestPendingStale**, **DomainOutboxPendingBacklog**, **DomainOutboxPostCommitDispatchFailures** в `dental_booking_alerts.yml`; Celery **`domain_outbox.dispatch_pending`**; метрики `domain_outbox_pending_rows`, `domain_outbox_oldest_pending_age_seconds` (см. [07_PHASE_2_RELIABILITY.md](../arch_plan/07_PHASE_2_RELIABILITY.md)).
5. **Гейт vs retry (1b-F6 / PRC-B4):** ручной **Retry** не обходит каталог — при расхождении суммы ожидайте **409** и код гейта; pytest `test_platform_force_retry_409_when_execute_catalog_gate_blocks` и см. §4.3 выше.
6. **Висящий платёж YooKassa vs TTL intent (10-Q8 / OPS + Product, без авто-refund в коде):** Celery **`platform_billing.expire_stale_signup_intents`** помечает просроченные intent со статусом вроде `pending_payment` / `payment_initiated` как **`expired`** по полю `expires_at` (см. `.env.example`, TTL при создании intent). Платёж у провайдера при этом может остаться в **`pending`** или перейти в **`succeeded`** позже, чем истёк intent. **OPS:** сопоставить `platform_subscription_payments` и кабинет YooKassa; при «осиротевшем» succeeded без активного intent — ручной разбор (возврат / сверка / тикет Product), а не автоматический refund из приложения без решения Product. Метрика наблюдаемости: **`platform_signup_intent_ttl_expired_total`** (инкремент при каждом TTL-expire job run для затронутых строк).

**Расширение `result` у `platform_billing_webhook_total` (гейт каталога, 2026-04):** помимо прежних значений возможны, в частности: `invalid_billing_period`, `billing_period_requires_plan_slug`, `unknown_plan_slug`, `amount_mismatch_catalog`, `missing_payment_amount` — при срабатывании гейта intent не переходит в `paid`; алерты и дашборды см. [05_PHASE_1D_OBSERVABILITY.md](../arch_plan/05_PHASE_1D_OBSERVABILITY.md), реестр [07_metrics_observability.md](../07_metrics_observability.md).

## 11. OpenAPI

Путь `POST /api/v1/platform/billing/webhooks/{provider}` описан в OpenAPI FastAPI: `response_model`, коды ошибок, пример тела уведомления — см. `src/api/v1/routers/platform_billing.py`. Публичный accept приглашения владельца: `POST /api/v1/public/platform/owner-invite/accept`. Внутренний выпуск токена (JWT Основателя): `POST /api/v1/platform/internal/signup-intents/{intent_id}/owner-invite-token`.

## 12. Возврат, chargeback и org после «денег назад» (ADR-012)

**Норматив:** [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md). Кратко для разработки:

| Этап | Поведение |
|------|-----------|
| Платёж не дошёл до устойчивого `succeeded` | Как сейчас: тенант полноценно не активируется по этому платежу |
| `succeeded` → провижининг → **затем** `refunded` (или эквивалент проигранного спора) | Зафиксировать событие **идемпотентно**; перевести подписку/intent в явное состояние **suspended / billing_revoked** (имя поля — миграция @ARCH); **отозвать** entitlements, выданные из `tariff_snapshot` этого signup; **сохранить** `Organization` для аудита и offboarding |
| Повтор webhook с тем же исходом | Без повторного «двойного отзыва» и без дублей смысла в аудите |
| Ручной reconcile / §25 | Только с аудитом; не обходить инварианты ADR-012 |

**Реализация (контур B, 2026-04):** признак «деньги назад → отзыв» централизован в `yookassa_payment_payload_indicates_full_refund_revocation` (`src/application/services/platform_yookassa_payment.py`): по OpenAPI объект **Payment** имеет enum **PaymentStatus** = `pending` \| `waiting_for_capture` \| `succeeded` \| `canceled` (без отдельного `refunded`); полный возврат часто виден как **`status=succeeded`** при **`refunded_amount` ≥ `amount`**. Дополнительно обрабатываются алиасные строки `status` (`refunded`, `chargeback`, …) из логов/интеграций. При срабатывании в `apply_platform_yookassa_notification` вызывается `apply_platform_billing_revocation_after_refund` (`platform_billing_service.py`): идемпотентный отзыв entitlements, маркер `saas.billing_revoked`, `intent` → `suspended` / `billing_revoked_at`; вход владельца — см. ADR-012; метрика `platform_billing_billing_revocation_total`.

Матрица **строк статуса YooKassa** (и аналогов) → внутренние переходы — вести в этом файле по мере расширения (согласование SEC/Product); для `refunded` базовый путь реализован как выше; прочие ветки (chargeback как отдельное событие провайдера и т.д.) — по мере появления требований.

### 12.1 Матрица «событие провайдера → обработчик» (контур B, YooKassa)

**Источник истины после приёма webhook:** ответ API YooKassa **GET Payment** (`object.id` = `provider_payment_id`), в первую очередь поле **`status`**. Расширения (вложенные объекты, отдельные типы уведомлений) — только после согласования **SEC/Product** и обновления этой таблицы.

| YooKassa Payment `status` (нормализуется к lower в коде) | Поведение в `apply_platform_yookassa_notification` | Метрики / метки webhook (ориентир) |
|----------------------------------------------------------|-----------------------------------------------------|-------------------------------------|
| `succeeded` | `pay.status=succeeded`; intent → `paid` / возврат `intent_id` на провижининг; идемпотентность `active`; guard `skipped_billing_revoked` при уже отозванном биллинге | `platform_billing_payment_lifecycle_total{event="succeeded"}`, `platform_billing_webhook_total` |
| `canceled` / `cancelled` | `pay.status=canceled` | `event="canceled"`, `ignored_status` |
| `refunded` (алиас вне строгого enum) | `pay.status=refunded`; отзыв ADR-012 | `event="refunded"`, `refund_reconciled` |
| `succeeded` + **полный** возврат (`refunded_amount` ≥ `amount`) | Канон OpenAPI; тот же отзыв | то же |
| `chargeback` / `disputed` / `dispute_lost` (алиасы) | Как отзыв выше | то же |
| `pending` | `pay.status=pending` | `event="pending"`, `ignored_status` |
| `waiting_for_capture` | `pay.status=waiting_for_capture` (без провижининга до `succeeded`) | `event="waiting_for_capture"`, `ignored_status` |
| иное значение | усечённое сохранение в `pay.status`, без смены доменного lifecycle intent | `event="other"`, `ignored_status` |

**Расширение (2026-04):** финальные статусы спора/chargeback, которые YooKassa может отдать отдельной строкой `status`, обрабатываются в одном блоке с `refunded` в `apply_platform_yookassa_notification` (см. код); при появлении новых значений — обновить таблицу после SEC/Product.

---

## Связанные документы

- [ADR-011](../../adr/ADR-011-platform-subscription-webhook-provisioning.md)  
- [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md)  
- [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md) — коды ошибок контуров A/B и reconcile  
- [PLATFORM_BILLING_PROVISION_RECONCILE.md](../../operations/PLATFORM_BILLING_PROVISION_RECONCILE.md) — OPS runbook: stuck/DLQ, Retry, manual-close  
- [data_migration_import_connectors.md](./data_migration_import_connectors.md) — другой модульный документ (паттерн оформления)
