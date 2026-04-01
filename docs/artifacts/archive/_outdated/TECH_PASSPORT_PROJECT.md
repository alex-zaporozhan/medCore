## 🗺 TECH_PASSPORT_PROJECT — Dental Booking (Project)

Режим:    SAAS  
Backend:  Python 3.11 + FastAPI + SQLAlchemy 2 (async) + Alembic + Redis + Celery  
Frontend: TypeScript + React 18 + Mantine + React Router + React Query + Vite + PWA  
БД:       PostgreSQL (основная), Redis (кеш/очереди), Celery (фоновая обработка)  
Почему:   Единое приложение для клиник/салонов, ориентированное на быстрый запуск, интеграции и омниканальную коммуникацию.

---

## 1. Цель и область проекта

- **Что это**: монолитное web‑приложение (backend + SPA/PWA frontend), решающее задачи записи клиентов, предоплаты, уведомлений и коммуникаций для клиник (изначально стоматология) и схожих бизнесов.
- **Ключевые сценарии**:
  - Онлайн‑запись пациентов к врачам/специалистам (пациентское PWA).
  - Рабочее место администратора с сеткой расписания, управлением записями, листом ожидания и предоплатой.
  - Омниканальный чат (Telegram, WhatsApp, VK, Instagram, email, web‑чат) с AI‑ассистентом.
  - Управление маркетингом (лента, сторис, акции) и recall‑кампаниями.
  - Базовые и AI‑отчёты по работе клиники, очередям и коммуникациям.

Проект технически разделён на Python‑backend (`/src`) и TypeScript‑frontend (`/frontend`), но разворачивается как единое приложение.

---

## 2. Структура репозитория (верхний уровень)

На основе `FILE_MAP.md` и фактических файлов:

- **Корень**:
  - `.cursorrules` — глобальные правила для AI‑системы.
  - `.env` (локально, не в git), `.env.example` — переменные окружения.
  - `pyproject.toml` — зависимости backend, тесты и инструменты.
  - `docker-compose.yml`, `Makefile` — инфраструктура запуска и утилиты.
  - `README.md` — инструкция для запуска (ориентирована на клиента).

- **Backend**:
  - `src/` — основной код приложения (FastAPI, домен, инфраструктура).
  - `alembic/` — миграции БД PostgreSQL.
  - `tests/` — тесты backend (API, безопасность, домен, сервисы).

- **Frontend**:
  - `frontend/` — SPA/PWA (React + Vite).
    - `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/**/*`.

- **Документация**:
  - `docs/` — ролевая система, процессы и проектные документы:
    - Системные: `ENGINEERING_PLAN.md`, `STACK_SELECTION.md`, `PROCESS_LAUNCH.md`, `TESTING_CANON.md`, `FILE_MAP.md` и др.
    - Проектные: `BUSINESS_LOGIC.md` (исторический), `DEVELOPMENT_PLAN.md`, `HANDOFF_AI_*`, архивные промпты в `docs/archive/aiChat/`.
    - Текущие технические паспорта: `TECH_PASSPORT_BACKEND.md`, `TECH_PASSPORT_FRONTEND.md`, этот файл.

---

## 3. Backend (краткое резюме, детали — в TECH_PASSPORT_BACKEND)

- **Стек**:
  - FastAPI (ASGI) + Uvicorn.
  - SQLAlchemy 2 async + asyncpg для PostgreSQL.
  - Alembic для миграций.
  - Redis для кеша, rate limiting, SMS‑кодов и Celery broker/result.
  - Celery для фоновых задач уведомлений и напоминаний.

- **Слои**:
  - `src/api/v1/` — роутеры FastAPI (пациент, админ, owner, интеграции, отчёты и др.).
  - `src/application/` — сервисы (use‑cases) и DTO.
  - `src/domain/` — доменные сущности и интерфейсы репозиториев.
  - `src/infrastructure/` — БД, репозитории, Celery, внешние API, rate limiter.
  - `src/core/` — конфиг, JWT/security, метрики, логирование, утилиты.

- **Домены**:
  - Клиника, врачи, услуги, пациенты.
  - Расписание и записи.
  - Предоплата, платежи, политики очереди, лист ожидания.
  - Уведомления, omnichannel чат, AI‑ассистент.
  - Recall‑кампании, маркетинговая лента, клиентские референсы.
  - Администраторы, планы, интеграции, скидки.

- **Интеграции**:
  - YooKassa, SMSC.ru‑совместимый SMS, SMTP, Telegram/WhatsApp/VK/Instagram/email webhooks, AI‑провайдер чат‑модели.

Подробности и ключевые пути: `docs/TECH_PASSPORT_BACKEND.md`.

---

## 4. Frontend (краткое резюме, детали — в TECH_PASSPORT_FRONTEND)

- **Стек**:
  - React 18 + TypeScript.
  - Mantine UI + кастомная тема.
  - React Router v6.
  - React Query v5.
  - Vite 6 + vite‑plugin‑pwa.

- **Основные зоны**:
  - Лэндинг `/`.
  - Пациентское PWA:
    - `/login`, `/oauth/result`, `/app`, `/booking/success`.
  - Админка:
    - `/admin/login`, `/admin/*` (dashboard, клиники, услуги, расписание, букинги, waitlist, recall, маркетинг, omni‑чат, отчёты, интеграции, стили, стикеры, администраторы, предоплата, скидки, политики уведомлений, соглашения).

- **Стейт и auth**:
  - `PatientAuthContext` — управление JWT пациента и `patientId`.
  - `AdminClinicContext` — выбор текущей клиники и бизнес‑лексикона.
  - `api/client.ts` — HTTP‑клиент с обработкой токенов и нормализацией ошибок.

Подробности и ключевые пути: `docs/TECH_PASSPORT_FRONTEND.md`.

---

## 5. Хранилища и миграции

- **СУБД**: PostgreSQL.
  - Все модели определены в `src/domain/entities/*.py`.
  - Миграции Alembic в `alembic/versions/*.py` покрывают:
    - Базу доменов (клиники, пациенты, врачи, услуги).
    - Записи, платежи, предоплату, очередь и лист ожидания.
    - Уведомления и omnichannel сущности.
    - Recall, маркетинг, AI‑аналитику.
- **Redis**:
  - `src/infrastructure/database/redis_client.py` — клиент.
  - Использование:
    - Rate limiting (`src/infrastructure/rate_limiter.py`).
    - Хранение SMS‑кодов авторизации.
    - Celery broker/result.
- **Очереди (Celery)**:
  - Конфиг: `src/infrastructure/messaging/celery_app.py`.
  - Таски: `src/infrastructure/messaging/tasks/notifications.py` (уведомления и напоминания).

---

## 6. Основные бизнес‑доменные области

(Фактическое состояние по коду; бизнес‑правила детально см. в отдельном бизнес‑документе.)

- **Организация/клиника**:
  - Модели: `Clinic`, `ClinicPlan`, `ClinicAiSettings`, `ClinicIntegrationSettings`, `ClinicPaymentGateway`, `AgreementSettings`.
  - Функции:
    - Настройки интеграций (платёжки, мессенджеры, AI).
    - Настройка бизнес‑лексикона (тип бизнеса, названия ролей).
    - Включение/настройка предоплаты, скидок, маркетинговых элементов и т.п.

- **Врачи/услуги**:
  - Модели: `Doctor`, `DoctorWorkingHours`, `DoctorAbsence`, `Service`, `ServiceDoctor`.
  - Функции:
    - Управление расписанием врача.
    - Привязка услуг к врачам и клинике.

- **Записи и оплатa**:
  - Модели: `Booking`, `Payment`, `PrepaymentPolicy`, `PrepaymentTransaction`, `QueuePolicy`, `WaitlistEntry`.
  - Функции:
    - Создание/изменение/отмена записей админом и пациентом.
    - Предоплата (опциональная) через YooKassa.
    - Лист ожидания и политики очереди (распределение слотов).

- **Коммуникации и уведомления**:
  - Модели: `Notification`, `NotificationChannelConfig`, `PatientCommunicationPreferences`, `WaitlistNotification`.
  - Функции:
    - Многоуровневая цепочка уведомлений (создание Notification → Celery‑таск → отправка через Telegram/SMS/Email).
    - Напоминания за 24h/2h до приёма.

- **Omnichannel и AI**:
  - Модели: `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`, `OmnichannelAuditLog`, `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`, `Conversation`, `ConversationAiAnalysis`.
  - Функции:
    - Единый чат по разным каналам (Telegram/WhatsApp/VK/Instagram/email/webchat).
    - Аналитика диалогов, AI‑отчёты и ассистент.

- **Маркетинг и recall**:
  - Модели: `PromoPost`, `Story`, `ClientReference`, `CsvImportJob`, `RecallCampaign`, `RecallSegment`, `RecallTemplate`, `RecallAutomation`, `RecallLog`.
  - Функции:
    - Маркетинговая лента и сторис в пациентском приложении.
    - Автоматизации возврата пациентов (recall‑кампании).

---

## 7. Интеграции и внешние зависимости (сводно)

Backend реализует следующие интеграции (см. подробности в TECH_PASSPORT_BACKEND):

- Платежи: YooKassa (`yookassa_client.py` + `/api/v1/payments`, `/api/v1/payments/webhook`).
- Мессенджеры:
  - Telegram, WhatsApp Business, VK, Instagram Direct, email inbound, webchat.
  - Webhooks через `src/api/v1/routers/integrations_gateway.py`.
- Уведомления:
  - SMS через SMSC.ru‑совместимый HTTP‑API (`sms_client.py`).
  - Email через SMTP (`email_sender.py`).
- AI‑провайдер:
  - Generic чат‑API (`ai_client.py`) с конфигурацией URL/ключа и модели.

Frontend использует только REST‑API backend и браузерные возможности (PWA, localStorage, fetch).

---

## 8. Тестирование и качество

- **Backend**:
  - Тестовый стек: `pytest`, `pytest-asyncio`, `pytest-playwright`.
  - Каталоги тестов:
    - `tests/api/` — API сценарии (платежи, интеграции, OAuth, врачи и др.).
    - `tests/security/` — безопасность платежей, персональных данных, чатов.
    - `tests/domain/`, `tests/services/` — доменные и сервисные тесты.
  - Конфигурация pytest — в секции `[tool.pytest.ini_options]` `pyproject.toml`.

- **Frontend**:
  - Тестовый стек: Vitest + Testing Library + JSDOM.
  - Скрипт `"test": "vitest"` в `frontend/package.json`.

- **Security‑аудит зависимостей**:
  - Backend: pip‑audit (через `tool.pip-audit` в `pyproject.toml`).
  - Frontend: `npm run security:audit` (`npm audit --production --audit-level=high`).

---

## 9. Ключевые файлы для RAG‑индексации

Рекомендуемый минимум для индексации и навигации ИИ по проекту:

- **Backend**:
  - `pyproject.toml`
  - `src/main.py`
  - `src/core/config.py`, `src/core/security.py`, `src/core/metrics.py`, `src/core/features.py`
  - `src/api/v1/router.py`, `src/api/v1/dependencies.py`, `src/api/v1/routers/*.py`
  - `src/application/services/*.py`, `src/application/dto/*.py`
  - `src/domain/entities/*.py`, `src/domain/interfaces/repositories/*.py`
  - `src/infrastructure/database/base.py`, `src/infrastructure/database/*_repo_impl.py`, `src/infrastructure/database/redis_client.py`
  - `src/infrastructure/external_apis/*.py`
  - `src/infrastructure/messaging/celery_app.py`, `src/infrastructure/messaging/tasks/notifications.py`
  - `src/infrastructure/rate_limiter.py`
  - `alembic/env.py`, все файлы `alembic/versions/*.py`

- **Frontend**:
  - `frontend/package.json`
  - `frontend/vite.config.ts`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/api/client.ts`, `frontend/src/api/types.ts`
  - `frontend/src/contexts/*.tsx`
  - `frontend/src/hooks/*.ts`
  - `frontend/src/admin/layouts/*.tsx`, `frontend/src/admin/pages/*.tsx`
  - `frontend/src/app/layouts/*.tsx`, `frontend/src/app/pages/*.tsx`
  - `frontend/src/shared/ui/*.tsx`, `frontend/src/shared/ErrorBoundary.tsx`

- **Документация (для контекста и промптов)**:
  - `docs/TECH_PASSPORT_BACKEND.md`
  - `docs/TECH_PASSPORT_FRONTEND.md`
  - `docs/TECH_PASSPORT_PROJECT.md` (этот файл)
  - Обновлённый `docs/BUSINESS_LOGIC_*.md` (см. отдельный документ бизнес‑логики)
  - `docs/STACK_SELECTION.md` (после обновления по фактическому стеку)

Этот технический паспорт фиксирует текущее состояние всего проекта на основе кода и конфигурации и предназначен как главный входной артефакт для RAG‑индексации и онбординга других ИИ/разработчиков.

