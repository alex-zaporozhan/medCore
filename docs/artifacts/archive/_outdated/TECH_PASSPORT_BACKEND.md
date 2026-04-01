## 🧩 TECH_PASSPORT_BACKEND — Dental Booking (Backend)

Режим:    SAAS  
Backend:  Python 3.11 + FastAPI + SQLAlchemy 2 (async)  
Frontend: TypeScript + React + Vite (отдельный паспорт)  
БД:       PostgreSQL + Redis + Celery (Redis broker/result)  
Почему:   Быстрый MVP для малого/среднего бизнеса с готовыми интеграциями (YooKassa, Telegram, SMS, AI, омниканал).

---

## 1. Общий обзор

- **Назначение**: backend‑API и фоновые процессы для системы записи и коммуникаций клиник (стоматология и смежные бизнесы).
- **Тип приложения**: монолитный сервис FastAPI, асинхронный стек.
- **Основные обязанности**:
  - REST API для пациентского приложения, админ‑панели и owner‑панели.
  - Управление клиниками, врачами, услугами, расписанием, записями, предоплатами.
  - Omnichannel‑чат (Telegram, WhatsApp, VK, Instagram, email, web‑чат) + AI‑ассистент.
  - Уведомления (SMS, Telegram, email) и напоминания о приёмах.
  - Отчёты и аналитика (включая AI‑отчёты по диалогам).

---

## 2. Технологический стек (runtime)

- **Язык**: Python 3.11 (`pyproject.toml`).
- **Web‑фреймворк**: FastAPI `^0.109.0`.
- **ASGI‑сервер**: Uvicorn `^0.27.0` (обычный способ запуска приложения).
- **Конфигурация**:
  - `pydantic` `^2.5.3`.
  - `pydantic-settings` `^2.1.0` — загрузка `.env`.
  - Файл настроек: `src/core/config.py` (`Settings`).
- **ORM / БД**:
  - SQLAlchemy `^2.0.25` (async ORM).
  - Драйвер PostgreSQL: `asyncpg` `^0.29.0`.
  - Миграции: Alembic `^1.13.1` (`alembic/`).
- **Кеш / брокер**:
  - Redis `^5.0.1` + `aioredis` `^2.0.1`.
  - Используется для: rate limiting, SMS‑коды, Celery broker/result, вспомогательное кеширование.
- **Очереди**:
  - Celery `^5.3.4` с extras `redis`.
  - Конфиг: `src/infrastructure/messaging/celery_app.py`.
- **Безопасность и auth**:
  - JWT: `python-jose[cryptography]` `^3.3.0`.
  - Хеширование паролей: `passlib[bcrypt]` `^1.7.4`.
- **Транспорт/интеграции**:
  - HTTP‑клиент: `httpx` `^0.26.0`.
  - Telegram Bot: `python-telegram-bot` `^20.7` (используется точечно, основной webhook реализован руками).
- **Dev‑tooling**:
  - Тесты: `pytest`, `pytest-asyncio`, `pytest-playwright`.
  - Линтеры/форматтеры: `ruff`, `black`, `mypy`.

Ключевой файл зависимостей: `pyproject.toml`.

---

## 3. Конфигурация и окружение

- **Источник конфигурации**: `src/core/config.py` (`Settings`), основан на `BaseSettings`.
- **Загрузка env**:
  - `env_file=".env"`, кодирует UTF‑8, регистр ключей неважен.
- **Ключевые параметры**:
  - `database_url`: строка подключения PostgreSQL (используется и в приложении, и в Alembic).
  - `redis_url`, `celery_broker_url`, `celery_result_backend`.
  - `jwt_secret_key`, `jwt_algorithm`, отдельные TTL для:
    - `jwt_access_token_expire_minutes_patient`.
    - `jwt_access_token_expire_minutes_admin`.
  - Параметры rate limiting:
    - Для SMS‑логина пациентов (`rate_auth_send_code_*`).
    - Для логина админов (`rate_admin_login_*`).
    - Для AI‑запросов (`rate_ai_*`).
  - Интеграции:
    - YooKassa: `yookassa_shop_id`, `yookassa_secret_key`, `yookassa_test_mode`, `yookassa_return_url`.
    - Telegram: `telegram_bot_token`, `telegram_admin_chat_id`, `telegram_webhook_secret`.
    - SMSC.ru: `smsc_login`, `smsc_password`, `smsc_sender`, `smsc_enabled`.
    - OAuth (пациент): `vk_*`, `yandex_*`.
    - SMTP: `smtp_*`.
    - AI‑провайдер: `ai_provider_*`.
- **Специальное поведение в тестах**:
  - Если `TESTING=1`, то валидация в `Settings` обнуляет лимиты для `rate_admin_login_*` (чтобы не получать 429 в тестах).

Ключевые файлы: `src/core/config.py`, `.env.example` (в корне), `alembic/env.py` (берёт `settings.database_url`).

---

## 4. Точка входа и жизненный цикл приложения

- **Главный модуль**: `src/main.py`.
  - Создаёт экземпляр `FastAPI`.
  - Настраивает CORS, логирование, метрики.
  - Подключает корневой роутер API: `src/api/v1/router.py` c префиксом `settings.api_v1_prefix` (по умолчанию `/api/v1`).
  - Определяет:
    - `/health` — простой health‑check.
    - `/metrics` — Prometheus‑совместимые метрики (если `metrics_enabled`).
  - Регистрирует глобальный обработчик исключений (`Exception` → 500 с логированием стектрейса и подсказкой о миграциях).

**Процессная модель**:

- ASGI‑сервер uvicorn обслуживает HTTP‑запросы (API).
- Отдельный процесс Celery‑воркера обрабатывает фоновые задачи (уведомления, напоминания).
- Redis обеспечивает:
  - Ключ/значение для rate limiting и SMS‑кодов.
  - Broker/result backend для Celery.

---

## 5. Архитектура слоёв и модулей

Логическая структура backend‑кода:

- **API (Transport Layer)** — `src/api/v1/`:
  - `router.py` — корневой роутер, подключает все `routers/*.py`.
  - `routers/*.py` — тематические модули:
    - Публичные и пациентские:
      - `auth.py`, `patients.py`, `services.py`, `public_services.py`, `schedule.py`,
        `bookings.py`, `patient_chat.py`, `patient_notification_settings.py`,
        `public_marketing.py`, `stickers.py` и др.
    - Админка:
      - `admin_auth.py`, `admin_services.py`, `admin_schedule.py`, `admin_doctor_schedule.py`,
        `admin_bookings` (в `bookings.py`), `admin_prepayment.py`, `admin_waitlist.py`,
        `admin_recall.py`, `admin_marketing.py`, `admin_reports.py`,
        `admin_doctors.py`, `admin_patients.py`, `admin_discount.py`,
        `admin_notification_policy.py`, `admin_integrations.py`,
        `admin_omni_chat.py`, `admin_channels.py`, `admin_client_reference.py`,
        `admin_payment_gateway.py`, `admin_styling.py`, `admin_stickers.py`,
        `admin_admins.py`, `admin_ai_settings.py`, `admin_ai_status.py`,
        `admin_ai_reports.py`, `admin_attention_feed.py` и др.
    - Owner / Omnichannel:
      - `owner_omni_channels.py`, `owner_omni_ai_settings.py`, `owner_omni_audit.py`.
    - Интеграции и webhooks:
      - `integrations_gateway.py` — вебхуки мессенджеров и web‑чата.
      - `csv_sync.py` — CSV‑импорт/экспорт.
  - Общие зависимости:
    - `dependencies.py` — `get_current_patient`, `get_current_admin`, доступ к БД и др.

- **Application Layer (use‑case‑уровень)** — `src/application/`:
  - Сервисы: `src/application/services/*.py`
    - Примеры:
      - Записи и расписание: `booking_service.py`, `schedule_service.py`.
      - Клиника/пациенты/врачи: `clinic_service.py`, `patient_service.py`, `doctor_service.py`.
      - Платежи и предоплата: `payment_service.py`, `clinic_payment_gateway_service.py`, `pricing_service.py`, `discount_service.py`.
      - Уведомления и сообщения: `notification_service.py`, `messaging_service.py`, `omnichannel_outbound_dispatcher.py`.
      - Omnichannel и AI: `omnichannel_chat_service.py`, `omnichannel_ai_orchestrator.py`, `omnichannel_integrations_config_service.py`, `chat_ai_service.py`, `conversation_analysis_service.py`, `omnichannel_ai_settings_service.py`.
      - Интеграционный шлюз: `integration_gateway_service.py`.
      - Аутентификация/авторизация: `auth_service.py`, `oauth_auth_service.py`.
      - Отчётность: `report_service.py`.
  - DTO и схемы: `src/application/dto/*.py`
    - Примеры: `booking_dto.py`, `auth_dto.py`, `payment_dto.py`, `schedule_dto.py`,
      `clinic_dto.py`, `doctor_dto.py`, `patient_dto.py`, `prepayment_dto.py`,
      `discount_dto.py`, `notification_policy_dto.py`, `omnichannel_dto.py`,
      `chat_ai_dto.py`, `waitlist_dto.py`, `attention_feed_dto.py`, `reports_dto.py`.

- **Domain Layer** — `src/domain/`:
  - Сущности: `src/domain/entities/*.py`
    - `clinic`, `clinic_ai_settings`, `clinic_plan`, `clinic_integration_settings`, `clinic_payment_gateway`, `agreement_settings`.
    - `doctor`, `doctor_working_hours`, `doctor_absence`.
    - `service`, `service_doctor`.
    - `patient`, `patient_communication_preferences`.
    - `booking`, `payment`, `prepayment_policy`, `prepayment_transaction`, `queue_policy`.
    - `waitlist_entry`, `waitlist_notification`.
    - `notification`, `notification_channel_config`.
    - `omnichannel_chat`, `omnichannel_message`, `omnichannel_contact`, `omnichannel_channel`, `omnichannel_audit_log`, `omnichannel_ai_settings`, `omnichannel_integration_config`.
    - `conversation`, `conversation_ai_analysis`.
    - `recall_campaign`, `recall_segment`, `recall_template`, `recall_automation`, `recall_log`.
    - `promo_post`, `story`, `client_reference`, `csv_import_job`.
    - `discount`, `admin_user`, `attention_feed` и др. (см. файлы в `src/domain/entities/`).
  - Интерфейсы репозиториев:
    - `src/domain/interfaces/repositories/*.py` — контракты для доступа к БД.

- **Infrastructure Layer** — `src/infrastructure/`:
  - БД и репозитории:
    - `database/base.py` — инициализация async engine и `AsyncSessionLocal`, базовый `Base`.
    - `database/*_repo_impl.py` — реализации репозиториев поверх SQLAlchemy.
    - `database/redis_client.py` — фабрика подключений к Redis.
  - Внешние API:
    - `external_apis/yookassa_client.py`, `sms_client.py`, `email_sender.py`, `ai_client.py`.
  - Очереди/таски:
    - `messaging/celery_app.py` — конфиг Celery и beat.
    - `messaging/tasks/notifications.py` — Celery‑таски по уведомлениям и напоминаниям.
  - Rate limiting:
    - `rate_limiter.py` — реализация счётчиков в Redis.

- **Core / Cross‑cutting** — `src/core/`:
  - `config.py` — настройки из `.env`.
  - `security.py` — JWT‑утилиты и функции для токенов.
  - `features.py` — фичфлаги.
  - `metrics.py` — Prometheus‑метрики.
  - `logging.py` — настройка логгера.
  - Утилиты: `ai_sanitizer.py`, `datetime_utils.py`, `encryption.py`, `user_messages.py`, `patient_messages.py` и др.

---

## 6. API‑контракты (высокоуровнево)

Полный список эндпоинтов определяется модулем `src/api/v1/router.py`, который подключает все `routers/*.py`. Ниже — основные группы:

- **Auth и пользователи**:
  - `/api/v1/auth/send-code`, `/verify-code`, `/agreement` — SMS‑логин пациента и получение настроек согласий.
  - `/api/v1/auth/oauth/vk/*`, `/oauth/yandex/*` — OAuth‑логин пациента через VK/Yandex.
  - `/api/v1/admin/auth/login` — логин админа по email/паролю.
  - `/api/v1/patients/*` — управление пациентами (поиск, деталка, обновление).

- **Клиники, врачи, услуги**:
  - `/api/v1/clinics/*` — инфо о клинике, настройки, бизнес‑план, интеграции.
  - `/api/v1/doctors/*` — список, расписание, статусы.
  - `/api/v1/services/*`, `/public/services/*` — каталог услуг.
  - Админские версии через `/api/v1/admin/...` (создание, редактирование, архивирование и т.п.).

- **Расписание и записи**:
  - Публичные/пациентские:
    - `/api/v1/doctors/{doctor_id}/schedule` — расписание врача.
    - `/api/v1/patient/bookings` — CRUD своими записями.
  - Админ:
    - `/api/v1/admin/bookings` — поиск/фильтрация записей.
    - `/api/v1/admin/bookings/{id}/cancel|complete|reschedule|no-show`.
    - `/api/v1/admin/clinics/{clinic_id}/schedule` — сводная сетка.

- **Оплаты и предоплата**:
  - `/api/v1/payments` — создание платежа по бронированию (YooKassa).
  - `/api/v1/payments/webhook` — webhook YooKassa для изменения статуса платежа.
  - `/api/v1/admin/prepayment/*` — управление политиками предоплаты.
  - `/api/v1/admin/payment-gateway/*` — настройки платёжных шлюзов клиники.

- **Waitlist и очередь**:
  - `/api/v1/admin/waitlist/*` — лист ожидания.
  - Политики очереди через `/api/v1/admin/queue-policy/*` (точные пути см. в роутерах).

- **Уведомления и коммуникации**:
  - `/api/v1/patient/notification-settings/*` — предпочтения пациента по каналам.
  - `/api/v1/admin/notification-policy/*` — политики уведомлений по клинике.

- **Omnichannel и чат**:
  - Пациент:
    - `/api/v1/patient/chat/*` — личный чат пациента (просмотр, отправка, удаление, отметка прочитано).
  - Админ/owner:
    - `/api/v1/admin/omni-chat/*` — интерфейс омниканального чата.
    - `/api/v1/owner/omni-channels/*`, `/owner/omni-ai-settings/*`, `/owner/omni-audit/*`.
  - Интеграции:
    - `/api/integrations/webhooks/telegram|whatsapp|vk|instagram|email` — обработка входящих сообщений из внешних каналов.
    - `/api/webchat/messages`, `/api/webchat/poll` — встроенный веб‑чат.

- **Маркетинг, recall и отчёты**:
  - `/api/v1/admin/recall/*` — сегменты, кампании, шаблоны, лог.
  - `/api/v1/admin/marketing/*` — промо‑лента, сторис, акции.
  - `/api/v1/public/marketing/*` — публичный маркетинговый контент.
  - `/api/v1/admin/reports/*`, `/admin/ai-reports/*`, `/admin/ai-status/*` — отчёты и AI‑отчёты.

Точная сигнатура эндпоинтов и DTO описана в соответствующих `routers/*.py` и `application/dto/*.py`.

---

## 7. Модель данных и миграции

- **СУБД**: PostgreSQL.
- **ORM**: SQLAlchemy 2 async (`src/infrastructure/database/base.py`).
- **Асинхронный движок**:
  - Создаётся в `database/base.py` на основе `settings.database_url`, пул управляем через параметры `db_pool_size`, `db_max_overflow`.
- **Миграции Alembic**:
  - Конфигурация: `alembic/env.py` (использует `settings.database_url`, `Base.metadata`).
  - Скрипты версий: `alembic/versions/*.py`.
  - Основные блоки миграций:
    - Базовые сущности: `Clinic`, `Patient`, `Doctor`, `Service`, `AdminUser`, базовая схема.
    - Бронирования и платежи: `Booking`, `Payment`, `PrepaymentPolicy`, `PrepaymentTransaction`, `QueuePolicy`.
    - Маркетинг: `PromoPost`, `Story`, `ClientReference`, `CsvImportJob`.
    - Omnichannel: `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`, `OmnichannelAuditLog`, `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`.
    - Recall/retention: `RecallCampaign`, `RecallSegment`, `RecallTemplate`, `RecallAutomation`, `RecallLog`.
    - Уведомления: `Notification`, `NotificationChannelConfig`, `WaitlistNotification`, `PatientCommunicationPreferences`.
    - Аналитика AI: `Conversation`, `ConversationAiAnalysis`.

**Ключевые инварианты и индексы** (по моделям и миграциям):

- **Booking**:
  - Уникальность слота врача: композитный уникальный индекс по `doctor_id`, `appointment_date`, `appointment_time`.
  - Индексы по клинике, врачу, пациенту и дате приёма для быстрых выборок.
- **Payment**:
  - Уникальный индекс по (`provider`, `provider_payment_id`).
  - Индекс по `booking_id`.
- **Omnichannel**:
  - Индексы по `chat_id`, `contact_id`, комбинациям `clinic_id + created_at` для эффективных выборок в чатах и аудит‑листе.

---

## 8. Внешние интеграции (backend‑часть)

Реальные (подтверждённые кодом) интеграции:

- **YooKassa**:
  - Клиент: `src/infrastructure/external_apis/yookassa_client.py`.
  - Используется в `application/services/payment_service.py`.
  - Основные операции:
    - `create_payment` → создаёт платёж, возвращает `provider_payment_id` и `confirmation_url`.
    - `get_payment` → получение статуса платежа.
  - API‑контракты:
    - `POST /api/v1/payments` — создание платежа.
    - `POST /api/v1/payments/webhook` — webhook статусов YooKassa.

- **SMS (SMSC.ru‑совместимый)**:
  - Клиент: `src/infrastructure/external_apis/sms_client.py`.
  - Использование:
    - Отправка SMS‑кодов логина (`AuthService.send_code`).
    - Потенциально — уведомления (через `NotificationService`/`send_with_fallback`).

- **Email (SMTP)**:
  - `src/infrastructure/external_apis/email_sender.py`.
  - Используется как один из fallback‑каналов для уведомлений.

- **Telegram / мессенджеры / web‑чат**:
  - Вебхуки: `src/api/v1/routers/integrations_gateway.py`.
  - Приведение к единому формату: `IntegrationGatewayService` (`src/application/services/integration_gateway_service.py`).
  - Поддерживаемые входящие источники:
    - Telegram (`/integrations/webhooks/telegram` + опциональный `X-Telegram-Bot-Api-Secret-Token`).
    - WhatsApp Business.
    - VK Messages.
    - Instagram Direct.
    - Входящий email.
    - Встроенный web‑чат (`/api/webchat/messages`, `/api/webchat/poll`).

- **AI‑провайдер (чат‑модель)**:
  - Клиент: `src/infrastructure/external_apis/ai_client.py`.
  - Конфиг через `Settings`: `ai_provider_base_url`, `ai_provider_api_key`, `ai_provider_model`.
  - Используется в:
    - `ChatAiService` — чат‑ассистент.
    - `OmnichannelAiOrchestrator`, `ConversationAnalysisService` — умный ассистент и аналитика переписок.

---

## 9. Аутентификация, авторизация и безопасность

**Пациентская аутентификация**:

- API: `src/api/v1/routers/auth.py`.
  - `POST /auth/send-code`:
    - Вход: телефон.
    - Нормализация номера, rate limit по IP и телефону через `RateLimiter`.
    - Генерация 6‑значного кода, сохранение в Redis, отправка через `SmsClient` (если включён) или лог.
  - `POST /auth/verify-code`:
    - Проверка кода из Redis.
    - Проверка согласий (AgreementSettings).
    - Создание/обновление `Patient`.
    - Выдача JWT через `create_access_token` (`role="patient"`).
  - OAuth через VK/Yandex:
    - Обмен кода на токен через внешнее API.
    - Поиск/создание пациента по `vk_id`/`yandex_id`.
    - Выдача JWT пациента.

- Извлечение текущего пациента:
  - `get_current_patient` в `src/api/v1/dependencies.py`:
    - Читает заголовок `Authorization: Bearer`.
    - Валидирует токен через `security.parse_access_token`.
    - Проверяет тип/роль токена.
    - Загружает `Patient` из БД.

**Админская аутентификация**:

- API: `src/api/v1/routers/admin_auth.py`.
  - `POST /admin/auth/login`:
    - Вход: email + пароль.
    - Rate limit по IP и email.
    - Проверка пароля через `passlib.pbkdf2_sha256`.
    - Выдача JWT с типом/ролью `type="admin"`, `clinic_id`.
  - Текущий админ:
    - `get_current_admin`/`get_current_admin_optional` (в `dependencies.py`):
      - Валидирует токен и загружает `AdminUser`.

**Роли и доступ**:

- Эндпоинты пациента используют `Depends(get_current_patient)` и, как правило, ограничены операциями над сущностями, привязанными к `patient_id`.
- Эндпоинты админа используют `Depends(get_current_admin)` и ограничены `clinic_id` в сущностях.
- Отдельных ролей внутри админов (например, кассир/врач) в коде не реализовано — одна роль `AdminUser`.

**JWT и секреты**:

- Создание и парсинг JWT: `src/core/security.py`.
  - Алгоритм: `HS256`.
  - Секрет: `settings.jwt_secret_key`.
  - Разные TTL для пациентов и админов.
- Секреты внешних сервисов берутся только из env (`Settings`), в коде нет хардкода токенов/ключей.

**Rate limiting и защита от брута**:

- Реализация в `src/infrastructure/rate_limiter.py`:
  - Счётчики в Redis с TTL.
  - Разделение по IP/телефону/email.
  - При превышении — исключение `RateLimitExceeded` → HTTP 429.

**Обработка ошибок и утечки данных**:

- Глобальный обработчик `Exception`:
  - Логирует стектрейс.
  - Возвращает короткое сообщение 500 без подробностей реализации.
- На уровне эндпоинтов:
  - Используются `HTTPException` с кодами 400/401/403/404/409 и контролируемыми сообщениями.

---

## 10. Уведомления, фоновые задачи и очереди

- **Celery**:
  - Конфиг: `src/infrastructure/messaging/celery_app.py`.
  - Broker/result: `settings.celery_broker_url`, `settings.celery_result_backend` (по умолчанию Redis).
  - Beat:
    - Периодический таск `notifications.run_reminders` каждые 15 минут.

- **Таски уведомлений** — `src/infrastructure/messaging/tasks/notifications.py`:
  - `send_booking_created_task`:
    - Загружает `Booking`, `Clinic`, `Patient`.
    - Создаёт сущность `Notification`.
    - Вызывает отправку через `NotificationService` / `send_with_fallback` (SMS/Telegram/email).
  - `send_booking_cancelled_task`.
  - `send_reminder_24h_task`, `send_reminder_2h_task`.
  - `run_reminders_task`:
    - Ищет подходящие `Booking` по времени/статусу.
    - Ставит задачи на отправку напоминаний.

- **Fallback‑логика каналов**:
  - Реализована в `NotificationService` и сопутствующих сервисах:
    - Приоритет: Telegram → SMS → Email (точный порядок см. в коде сервиса).
    - Использует `PatientCommunicationPreferences`, `NotificationChannelConfig`.

---

## 11. Наблюдаемость и эксплуатация

- **Логирование**:
  - Настройка: `src/core/logging.py`.
  - Уровень/формат управляются через `Settings` (`log_level`, `log_format`, по умолчанию json).

- **Метрики**:
  - Prometheus‑метрики: `src/core/metrics.py`.
  - Эндпоинт `/metrics` в `src/main.py`, включается если `settings.metrics_enabled`.

- **Health‑checks**:
  - `/health` — базовая проверка живости сервиса (без вызова БД).

---

## 12. Тестирование backend

- **Фреймворк тестов**:
  - `pytest` + `pytest-asyncio` (async‑тесты).
  - Конфиг: секция `[tool.pytest.ini_options]` в `pyproject.toml`.

- **Основные группы тестов**:
  - API‑тесты: `tests/api/*.py`
    - `test_payments.py` — платёжный флоу и webhook.
    - `test_integrations_gateway.py` — вебхуки мессенджеров.
    - `test_doctors.py` — эндпоинты врачей/расписания.
    - `test_auth_oauth.py` — OAuth‑флоу для пациентов.
  - Security‑тесты: `tests/security/*.py`
    - `test_security_kassa.py` — безопасность платёжного шлюза.
    - `test_security_chats.py` — безопасность чатов.
    - `test_security_pd.py` — защита персональных данных.
  - Domain/services‑тесты:
    - `tests/domain/test_omnichannel_chat.py`.
    - `tests/services/test_unified_chat_bridge.py`.

- **Особенности окружения тестов**:
  - `TESTING=1` отключает rate limit для логина админов.
  - Тесты могут использовать отдельную БД/Redis‑инстанс или in‑memory‑варианты (см. фикстуры в папке `tests/`).

---

## 13. Ключевые файлы backend (для RAG и навигации)

- **Конфигурация и запуск**:
  - `pyproject.toml`
  - `src/main.py`
  - `src/core/config.py`
  - `src/core/security.py`
  - `src/core/metrics.py`
  - `src/core/features.py`
  - `src/core/logging.py`

- **API и зависимости**:
  - `src/api/v1/router.py`
  - `src/api/v1/dependencies.py`
  - `src/api/v1/routers/*.py`

- **Приложение и домен**:
  - `src/application/services/*.py`
  - `src/application/dto/*.py`
  - `src/domain/entities/*.py`
  - `src/domain/interfaces/repositories/*.py`

- **Инфраструктура**:
  - `src/infrastructure/database/base.py`
  - `src/infrastructure/database/*_repo_impl.py`
  - `src/infrastructure/database/redis_client.py`
  - `src/infrastructure/external_apis/*.py`
  - `src/infrastructure/messaging/celery_app.py`
  - `src/infrastructure/messaging/tasks/notifications.py`
  - `src/infrastructure/rate_limiter.py`

- **Миграции**:
  - `alembic/env.py`
  - `alembic/versions/*.py`

Этот файл фиксирует фактическое состояние backend‑части проекта по коду и конфигурации и должен использоваться как источник правды для любых последующих архитектурных решений и RAG‑индексации.

