## HANDOFF — фактический протокол продукта и стека

**Цель файла** — дать компактное, техническое и актуальное описание того, что уже реализовано в кодовой базе, без ссылок на бизнес‑документы и устаревшие планы.

- **Использовать как**: исходный контекст для ИИ‑агентов и инженеров перед любыми доработками.
- **Источник правды**: только код, конфиги, Docker и env‑шаблоны в репозитории на момент последнего обновления файла.

---

## 1. Что это за продукт

- **Тип**: универсальная веб‑платформа (SaaS) для сервисных бизнесов c моделью «запись на услуги» (по умолчанию — стоматологическая клиника).
- **Наслоение**:
  - Пациентская PWA: онлайн‑запись, чат, лента/история, авторизация.
  - Админ‑панель клиники: расписание, записи, услуги, врачи, пациенты, маркетинг, кампании, отчёты, интеграции, настройки, чат и AI‑ассистент.
- **Архитектура**:
  - Backend: монолитный сервис на FastAPI с DDD‑подобной модульной структурой.
  - Frontend: единый React SPA (Vite) с разделением на пациентскую и админ‑зону.
  - Инфраструктура: PostgreSQL, Redis, Celery, Docker / docker‑compose.

---

## 2. Технологический стек

### 2.1 Backend

- **Язык**: Python 3.11 (`pyproject.toml`).
- **Web‑фреймворк**: FastAPI (`src/main.py`, `src/api/v1/router.py`, `src/api/v1/routers/*.py`).
- **Сервер**: Uvicorn (локальный запуск и Docker CMD).
- **База данных**:
  - PostgreSQL 15 (`docker-compose.yml` сервис `postgres`).
  - SQLAlchemy 2.x (async) + `asyncpg` (`src/infrastructure/database/*`).
  - Alembic миграции (`alembic/env.py`, `alembic/versions/*.py`).
- **Конфигурация**:
  - Pydantic 2 + `pydantic-settings` (`src/core/config.py`).
  - `.env.example` описывает полный набор нужных переменных окружения (DB, Redis, очереди, интеграции, AI).
- **Очереди и фон**:
  - Celery (`src/infrastructure/messaging/celery_app.py`).
  - Redis (`docker-compose.yml` сервис `redis`).
  - Таски: `src/infrastructure/messaging/tasks/*.py` (уведомления, рассылки, вспомогательные фоновые операции).
- **Безопасность**:
  - JWT‑аутентификация (`src/core/security.py`, роуты `auth.py`, `admin_auth.py`).
  - Пароли через `passlib[bcrypt]`.
  - Базовая настройка логирования (`src/core/logging.py`).

### 2.2 Frontend

- **Язык**: TypeScript + TSX.
- **Фреймворк**: React 18.
- **Роутер**: React Router (`frontend/src/main.tsx`, `App.tsx`).
- **UI‑библиотека**: Mantine (`@mantine/core`, `@mantine/hooks`).
- **Data‑layer**: `@tanstack/react-query` + feature‑hooks (`frontend/src/hooks/*`).
- **Сборка**: Vite (`frontend/package.json`, `vite` + `@vitejs/plugin-react`).
- **PWA**:
  - `vite-plugin-pwa`.
  - Service worker и манифест (`frontend/src/pwa`, артефакты билда в `frontend/dist`).

### 2.3 Инфраструктура и инструменты

- **Контейнеризация**: Docker multi‑stage `Dockerfile` для backend (Poetry builder → slim runtime).
- **Оркестрация (dev)**: `docker-compose.yml` поднимает:
  - API (FastAPI + Uvicorn),
  - Postgres,
  - Redis,
  - Celery worker,
  - Celery beat.
- **Управление зависимостями**:
  - Backend: Poetry.
  - Frontend: npm/yarn.
- **Тулчейн качества**:
  - Линтеры и форматтеры: `ruff`, `black`.
  - Статический анализ: `mypy`.
  - Тесты: `pytest`, `pytest-asyncio`, `pytest-playwright`.

---

## 3. Фактическая архитектура backend

- **Основное дерево `src/`**:
  - `src/api/v1/` — REST‑слой на FastAPI:
    - `router.py` агрегирует все v1‑роутеры.
    - `routers/*.py` — модули по доменам (bookings, schedule, services, clinics, doctors, patients, payments, waitlist, recall, marketing, notifications, reports, chat, AI, CSV‑sync и др.).
  - `src/domain/entities/` — доменные сущности:
    - клиника, врач, администратор, пациент;
    - запись, расписание, политика предоплаты, платеж, план клиники;
    - waitlist, очередь, уведомление, настройки каналов;
    - recall‑кампании, сегменты, шаблоны, логи;
    - маркетинг (stories, промо‑посты, скидки, отзывы);
    - чат, сообщения, разговоры, attention‑feed;
    - CSV‑импорт и другие вспомогательные модели.
  - `src/application/services/` — прикладные сервисы / use‑cases:
    - `booking_service`, `schedule_service`, `clinic_service`, `doctor_service`, `patient_service`;
    - `payment_service`, `prepayment_service`;
    - `waitlist_service`, `recall_service`, `marketing_service`;
    - `notification_service`, `messaging_service`;
    - `chat_service`, `chat_ai_service`, `attention_feed_service`;
    - `csv_import_service`, `report_service` и др.
  - `src/infrastructure/database/`:
    - создание engine/сессий;
    - SQLAlchemy‑модели и репозитории под доменные сущности.
  - `src/infrastructure/messaging/`:
    - конфигурация Celery‑приложения;
    - задачи в `tasks/` (отправка уведомлений, запуск кампаний и фоновых сценариев).
  - `src/infrastructure/external_apis/`:
    - `yookassa_client.py` — платежи;
    - `sms_sender.py` — SMS через SMSC.ru;
    - `email_sender.py` — SMTP‑отправка;
    - `telegram_sender.py` — Telegram‑нотификации;
    - `ai_client.py` — HTTP‑клиент к внешнему AI‑провайдеру.
  - `src/core/` — конфиг, логирование, безопасность, утилиты времени.
  - `src/scripts/seed_demo_data.py` — заполнение демо‑данными.
- **Паттерн**: модульный монолит, разделённый на слои:
  - domain (модели),
  - application (бизнес‑операции),
  - infrastructure (БД, очереди, интеграции),
  - api (REST‑контроллеры).

---

## 4. Фактическая архитектура frontend

- **Главные зоны**:
  - `frontend/src/app/pages/` — пациентские страницы:
    - домашняя, мастер записи, страница успеха;
    - логин, история/лента, чат.
  - `frontend/src/admin/pages/` — админ‑панель:
    - дешборд;
    - записи, расписание, расписание врачей;
    - клиники, врачи, услуги, пациенты, администраторы;
    - предоплата, платёжный шлюз;
    - waitlist, recall‑кампании, маркетинг, стикеры, скидки, отзывы, лента;
    - отчёты и аналитика;
    - каналы уведомлений и соглашения;
    - чат с пациентами, AI‑ассистент, attention‑feed;
    - общие настройки и стили.
  - `frontend/src/admin/components/` и `frontend/src/admin/layouts/` — UI‑компоненты и layout‑ы.
  - `frontend/src/hooks/` — feature‑hooks для доступа к API (bookings, schedule, waitlist, recall, marketing, payments, reports, chat, AI и др.).
  - `frontend/src/api/` — HTTP‑клиент, TS‑типы запросов/ответов.
  - `frontend/src/shared/` — общие UI‑элементы и утилиты.
- **Паттерн**:
  - SPA, организованная по фичам.
  - Все запросы к backend проходят через `api/` + hooks с React Query.

---

## 5. Основные возможности (чисто по коду)

- Онлайн‑запись к врачу по услугам и слотам расписания.
- Управление расписанием, услугами, врачами, клиниками и администраторами.
- Предоплата и онлайн‑платежи (YooKassa) с политиками предоплаты.
- Мультиканальные уведомления (SMS, email, Telegram) с настройками политик и предпочтений пациента.
- Лист ожидания (waitlist) и политики очереди для автоматического добора пациентов.
- Recall‑кампании и ре‑активация пациентов по сегментам и шаблонам.
- Маркетинговые активности (истории, промо‑посты, скидки, отзывы, стикеры).
- Двусторонний чат пациент–клиника + AI‑ассистент и attention‑feed для приоритизации задач.
- Отчёты и аналитика по ключевым метрикам (записи, выручка, активность, кампании).
- CSV‑импорт данных из внешних систем.

### 5.1 Универсальный бизнес и «теневые» вертикали (по коду)

- В backend DTO `src/application/dto/clinic_dto.py` определён `BusinessType = Literal["stomatology", "clinic", "beauty_salon", "barbershop", "nail_salon", "massage_salon", "other"]`:
  - платформа умеет различать как минимум: стоматологию, клинику общего профиля, **салон красоты**, **барбершоп**, **салон маникюра**, **массажный салон** и произвольный тип (`other`).
- В доменной сущности `src/domain/entities/clinic.py` есть поля `business_type` и `business_type_custom_name`, а Alembic‑миграция `add_clinics_business_type.py` добавляет их в таблицу `clinics` — это не просто идея, а физическое поле в БД.
- В сервисе `src/application/services/business_lexicon_service.py` описаны словари ролей/лексики по типу бизнеса:
  - например, для beauty/barber‑вертикалей присутствуют роли `"barber"` и `"pedicure_master"`, с человекочитаемыми названиями;
  - сервис подбирает лексикон интерфейса и ролей исходя из `clinic.business_type`.
- На frontend:
  - `frontend/src/api/types.ts` содержит `BUSINESS_TYPE_OPTIONS` с теми же значениями и тип `BusinessType`;
  - `frontend/src/admin/pages/AdminClinicsPage.tsx` даёт администратору выбирать `business_type` и настраивать `business_type_custom_name`.
- В тестах `tests/api/test_stage1_universal_business.py` явно проверяется:
  - что `GET /api/v1/clinics` возвращает `business_type`, `business_type_custom_name` и бизнес‑лексикон;
  - что `PUT /api/v1/clinics/{id}` позволяет обновлять `business_type` (например, в `"beauty_salon"`).
- Фактический вывод по коду: **платформа уже реализована как универсальный движок записи для разных сервисных бизнесов**, где стоматология — дефолтный профиль, а остальные вертикали переключаются через `business_type` и связанные словари лексики.

---

## 6. Интеграции и ключевые ENV‑переменные

- **База/очереди**:
  - `DATABASE_URL`, `REDIS_URL`, параметры Postgres/Redis.
- **Платежи (YooKassa)**:
  - `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_TEST_MODE`, `YOOKASSA_RETURN_URL`.
- **SMS (SMSC.ru)**:
  - `SMSC_LOGIN`, `SMSC_PASSWORD`, `SMSC_SENDER`.
- **Email (SMTP)**:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`.
- **Telegram**:
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`.
- **AI‑провайдер**:
  - `AI_PROVIDER_BASE_URL`, `AI_PROVIDER_MODEL`, `AI_PROVIDER_API_KEY`, `AI_TIMEOUT_SECONDS`.

---

## 7. Где искать опору для доработок

- **Контракты и типы**:
  - Backend DTO и схемы — в `src/api/v1` и рядом с сервисами.
  - Frontend типы — `frontend/src/api/types.ts` + auto‑inferred из hooks.
- **Повторное использование паттернов**:
  - Для новых доменных фич — смотреть уже реализованные сущности и сервисы в `src/domain/entities` и `src/application/services`.
  - Для новых API — копировать структуру существующих роутеров в `src/api/v1/routers`.
  - Для новых UI‑экранов — повторять подход страниц и hooks в `frontend/src/admin/pages` или `frontend/src/app/pages`.

