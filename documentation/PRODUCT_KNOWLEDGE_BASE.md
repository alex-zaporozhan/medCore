# PRODUCT KNOWLEDGE BASE — Dental Booking

> **Версия:** 2026-04-02 | **Статус:** CANONICAL (публичный git) | **Аудитория:** AI-агент, поддержка, онбординг
> **Источник фактов:** `pyproject.toml`, `src/main.py`, `src/api/v1/router.py`, `frontend/src/routePaths.ts`, `frontend/src/admin/layouts/AdminLayout.tsx`, `frontend/src/config/edition.ts`, `docker-compose.yml`, `src/application/rbac_matrix.py`, `src/core/config.py`, `src/application/services/booking_status_service.py`, `src/application/multitenancy.py`, `tests/e2e/test_booking_to_payment.py`.

## 1. ИДЕНТИЧНОСТЬ ПРОДУКТА

- **Название:** Dental Booking (пакет `dental-booking`, `settings.app_name` по умолчанию `dental-booking`).
- **Категория:** B2B SaaS / операционная платформа для стоматологической клиники.
- **Одна фраза:** Веб-приложение: маркетинг и запись, админка для операций клиники, PWA для пациента, REST API на FastAPI.
- **Проблема:** Свести запись, коммуникации, часть финансов/маркетинга и задач в одну кодовую базу с изоляцией по клинике (tenant).
- **Дифференциатор (рынок):** [ТРЕБУЕТ ПРОВЕРКИ @BIZ] — публичный конкурентный аудит не ведётся.

## 2. ТЕХНИЧЕСКИЙ СТЕК

| Компонент | Факт |
|-----------|------|
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| БД | PostgreSQL (async SQLAlchemy, asyncpg), Alembic |
| Кэш / брокер | Redis |
| Очереди | Celery (`src.infrastructure.messaging.celery_app`) |
| Frontend | Vite, React, TypeScript, Mantine |
| Auth | JWT (PyJWT), отдельные TTL админа/пациента в Settings |
| Прочее | httpx, python-telegram-bot, boto3 (S3-совместимое хранилище медфайлов) |
| Тесты | pytest, pytest-asyncio, pytest-playwright |
| Docker | Compose: Postgres 16, Redis 7, backend, celery, celery-beat, frontend |

## 3. АРХИТЕКТУРА

- **Тип:** модульный монолит (один процесс API + фронтенд-бандл).
- **API:** REST, префикс `Settings.api_v1_prefix` (по умолчанию `/api/v1`); в `main.py` дублируется алиас `/api/v1` при другом значении настройки.
- **Swagger/ReDoc:** в `app_env=production` отключены; иначе `/docs`, `/redoc`.
- **Наблюдаемость:** Prometheus, `/health`, `/health/replica`, `/health/s3`, `/metrics`.
- **Слои:** `api` → `application` → `domain` → `infrastructure`.
- **События:** при старте регистрируются обработчики CRM, ERP, лояльности, задач, маркетинговой атрибуции.
- **Фронт:** канон путей в `frontend/src/routePaths.ts`.

## 4. РОЛИ И ПРАВА

- **Админка `/admin`:** системные коды ролей в сиде: `owner`, `manager`, `admin`, `doctor` (`SYSTEM_ROLE_CODES`). Настраиваемые права через матрицу; список кодов в `documentation/rbac_router_permissions.txt`; гайд `RBAC_RIGHTS_POLICIES_GUIDE.md`.
- **PWA `/app`:** пациентские сценарии по маршрутам в `routePaths.ts`.

## 5. МОДУЛИ И URL

### 5.1 Общие правила

- **Админка:** сегменты из `ADMIN_SHELL_ROUTE_SEGMENTS` (`routePaths.ts`) → URL `/admin/{сегмент}`. Дашборд: `/admin` (index). Вход: `/admin/login`. Деталь задачи: `/admin/tasks/:taskId`.
- **PWA пациента:** `/app` (главная) и сегменты из `PATIENT_APP_ROUTE_SEGMENTS`: `feed`, `booking`, `history`, `loyalty`, `forms`, `chat`, `profile`.
- **Маркетинг:** `/` (лендинг), публичный профиль врача `/:clinicSlug/doctors/:doctorSlug` (`App.tsx`).
- **Пациент без сессии:** `/login`, OAuth `/oauth/result`, подтверждение записи `/booking/success`.
- **API:** префикс по умолчанию `/api/v1`; состав и порядок подключения роутеров — `src/api/v1/router.py`; человекочитаемая таблица префиксов — **`documentation/API_V1_ROUTER_MANIFEST.md`** (синхронизировать при изменении `include_router`). Построчная сводка по каждому модулю (пути, метрики, pytest): **`documentation/router_surface/INDEX.md`** (`python scripts/generate_router_surface_docs.py`). Документатор: **`documentation/SCRIBE_ROUTER_CHECKLIST.md`**.

### 5.2 Админка: таблица сегментов (код)

Колонки **«Сайдбар»** и **«Заголовок (ContextBar)»** сняты с `AdminLayout.tsx` (навигация) и соответствующих страниц в `frontend/src/admin/pages/` (или `SchedulePage.tsx`). Если в сайдбаре нет пункта — раздел открывается по прямому URL или из внутренних ссылок.

| Сегмент | URL | Сайдбар (`AdminLayout`) | Заголовок страницы (ContextBar и т.п.) |
|--------|-----|-------------------------|----------------------------------------|
| — | `/admin` | Лента | Лента (`AdminDashboardPage` — дашборд дня + staff feed; см. `USER_DOCS/ADMIN_DASHBOARD.md`) |
| — | `/admin/login` | — | Вход в админку (`AdminLoginPage`) |
| staff-chat | `/admin/staff-chat` | Чат команды | Чат команды |
| me | `/admin/me` | Личный кабинет | Личный кабинет |
| calendar | `/admin/calendar` | Календарь | Календарь |
| knowledge | `/admin/knowledge` | База знаний | База знаний |
| clinics | `/admin/clinics` | Клиники | Клиники |
| services | `/admin/services` | Услуги | Услуги |
| schedule | `/admin/schedule` | Расписание | Расписание |
| tasks | `/admin/tasks` | Задачи (Kanban) | Задачи (`AdminTasksPage`; для лида — см. `leads-log`) |
| leads-log | `/admin/leads-log` | Лиды (лог), если есть право | Лиды (лог) (`AdminLeadsLogPage` → тот же канбан-поверхность) |
| bookings | `/admin/bookings` | Записи | Записи |
| prepayment | `/admin/prepayment` | Предоплата | Предоплата |
| waitlist | `/admin/waitlist` | Очередь | Очередь ожидания |
| recall | `/admin/recall` | Recall | Recall / Автоматизации |
| marketing | `/admin/marketing` | Маркетинг | Маркетинг |
| retention | `/admin/retention` | Retention | Retention (Smart Retention Engine) |
| sales | `/admin/sales` | CRM & Sales | CRM‑воронка продаж |
| attention | `/admin/attention` | — | Стена объявлений |
| reports | `/admin/reports` | Analytics / Reports | Отчёты и дашборд (при загрузке возможен этап «Отчёты») |
| finance | `/admin/finance` | Finance | Финансы и ERP |
| loyalty | `/admin/loyalty` | Loyalty | Абонементы и лояльность |
| forms | `/admin/forms` | — | Формы и документы |
| doctors | `/admin/doctors` | Врачи | Врачи |
| doctor-schedule | `/admin/doctor-schedule` | Расписание врачей | График врачей |
| patients | `/admin/patients` | Пациенты (при праве) | Пациенты |
| omni-chat | `/admin/omni-chat` | Чат с клиентом | Omni‑чат — только работа |
| omni-channels | `/admin/omni-channels` | — | Омниканальные каналы |
| omni-ai-settings | `/admin/omni-ai-settings` | — | AI омниканального ассистента |
| channels | `/admin/channels` | — | Каналы уведомлений |
| integrations | `/admin/integrations` | — | Интеграции |
| omni-vault | `/admin/omni-vault` | — | Omni-Vault (медиа и экспорт) |
| styling | `/admin/styling` | — | Оформление |
| stickers | `/admin/stickers` | — | Стикеры |
| settings | `/admin/settings` | Настройки | Настройки |
| administrators | `/admin/administrators` | Персонал | Персонал |
| payment-gateway | `/admin/payment-gateway` | — | Платёжный шлюз (в части состояний — «Касса») |
| client-reference | `/admin/client-reference` | — | Справка для клиента |
| discounts | `/admin/discounts` | — | Скидки и акции |
| notification-policy | `/admin/notification-policy` | — | Политика уведомлений |
| agreements | `/admin/agreements` | — | Соглашения |
| rights-policies | `/admin/rights-policies` | Права и политики (при праве) | Права и политики (`rbacRightsPoliciesPageCopy.ts`, RU) |

**Видимость сайдбара (код):** пункт «Пациенты» скрыт без права `patients.pii.read` (`ADMIN_PERM_PATIENTS_PII_READ`); «Права и политики» — без `rbac.manage`; «Лиды (лог)» — без `leads.log.view`. **Редакция Box:** при `VITE_EDITION` ∈ `{basic, box}` (`isBoxEdition()`) из сайдбара убираются пути `/admin/sales` и `/admin/retention`, а прямой заход на эти сегменты даёт редирект на `/admin` (`isAdminSegmentBlockedInBox`).

### 5.3 PWA пациента (код)

Нижняя/основная навигация в `AppLayout.tsx`: **Главная** `/app`, **Запись** `/app/booking`, **Чат** `/app/chat`, **Профиль** `/app/profile`; **История** `/app/history` вынесена в расширенный список (`mainNavWithHistory`). Остальные сегменты (`feed`, `loyalty`, `forms`) доступны по URL и внутренним ссылкам.

### 5.4 Статические path для регрессии и динамические маршруты

- **`buildDerivedPublicAppPaths()` / `ALL_PUBLIC_APP_PATHS`** (`routePaths.ts`) — **только фиксированные** path (лендинг, `/admin/*` по сегментам, `/app/*`, `/login`, `/oauth/result`, `/booking/success`). Используется в тестах на уникальность и паритет с `ROUTE_PATHS`.
- **Динамические** публичные маршруты в дереве React Router, но **не** в этом списке: профиль врача **`/:clinicSlug/doctors/:doctorSlug`** (`PublicDoctorProfilePage`). Для приёмки их проверяют отдельно (ручной или E2E-сценарий по шаблону).

## 6. БИЗНЕС-ПРАВИЛА (подтверждено кодом)

### 6.1 Платформа и API

1. Мультитенантность: сущности с `clinic_id`; проверки границ клиники — `assert_entity_belongs_to_clinic` и родственная логика в `src/application/multitenancy.py` (несовпадение клиники → запрет/«не найдено» на границе API по правилам маршрута).
2. HTTPException: ответ с `detail`, `code`, опционально `trace_id`.
3. 500: без утечки внутренностей, опционально `trace_id`.
4. 422: `VALIDATION_ERROR` и безопасный список ошибок.
5. Trace ID: middleware `X-Trace-Id`.
6. Production: без интерактивной OpenAPI UI.
7. Аудит колонок tenant в схеме БД: `scripts/audit_tenant_columns.py` (инфраструктурная проверка, не замена доменных правил).

### 6.2 Запись (booking): FSM статусов

Централизованная машина состояний — `BookingStatusService` в `src/application/services/booking_status_service.py`. Переходы разрешены только парами из `_rules` (например: из `pending` → `confirmed`, `registered`; из `confirmed`/`pending`/`registered` → `in_progress`; завершение → `completed`; `no_show` и `cancelled` из набора допустимых исходных статусов; `awaiting_payment` → `confirmed` или отмена). Попытка неразрешённого перехода → `ValueError` на уровне сервиса. Комментарий в коде описывает сценарии ресепшена и предоплаты.

### 6.3 Пациентский вход и оплата (регрессионный тест)

В `tests/e2e/test_booking_to_payment.py` зафиксирован сквозной сценарий: health → `POST /api/v1/auth/send-code` (код в Redis) → `verify-code` → список врачей/услуг → слоты расписания → создание записи → создание платежа (с моком) с проверкой `payment_url`. Это не полный перечень продуктовых правил, но подтверждает контракт основного happy-path.

### 6.4 Идемпотентность событий (unit)

Для стабильности CRM/задач проверяется детерминированность/идемпотентность вспомогательных идентификаторов событий записи — см. `tests/unit/test_booking_event_dedup.py`.

### 6.5 Staff / объявления (UI)

Модерация комментариев к постам на «Стене объявлений» (`/admin/attention`): право `staff.feed.comments.moderate` или роль `owner` (код `AdminEmergencyNotificationsPage.tsx`).

## 7. КОНКУРЕНЦИЯ

[ТРЕБУЕТ ПРОВЕРКИ @BIZ]

## 8. МАСШТАБ

- Файлов роутеров в `src/api/v1/routers/`: 80 `.py` на дату версии (включая вспомогательные модули пакета).
- **Фиксированные** публичные path приложения (фронт): `ALL_PUBLIC_APP_PATHS` в `routePaths.ts`; динамические шаблоны — §5.4.

## 9. ГЛОССАРИЙ

| Термин | Значение |
|--------|----------|
| Клиника | Tenant |
| Админка | `/admin` |
| PWA | `/app` для пациента |
| Staff chat | Внутренний чат персонала |
| Omni chat | Инбокс с пациентами по внешним каналам |

## ПРОБЕЛЫ

- **[UNDOCUMENTED]** UI без отражения в `routePaths` или роутерах — завести задачу на канон.
- **USER_DOCS:** отдельные end-user страницы не покрывают все сегменты админки — см. объём v1 в `documentation/USER_DOCS/INDEX.md`.

Reference: `documentation/PROJECT_REPOSITORY_LAYOUT.md` · `documentation/SALES_PITCH.md` · `frontend/src/routePaths.ts`
