# Техническое резюме для due diligence — dental_booking (с опорой на факты из репозитория)

Охват: обзор кодовой базы (бэкенд `src/`, `tests/`, `frontend/`, `deploy/`, `alembic/`, CI). Метрики ниже — по состоянию рабочей копии на момент аудита, если не указано иное.

---

## 1. Данные и изоляция мультитенантности

**Как реализована мультитенантность**

- **Основной ключ тенанта — `clinic_id`:** в JWT администратора в payload попадает `clinic_id`; в потоках пациента/бронирования на сущностях последовательно проверяется принадлежность к `clinic_id` (например, сервис бронирования вызывает `assert_entity_belongs_to_clinic` из `src/application/multitenancy.py`).
- **Уровень организации / сети:** поле `organization_id` используется у админов, клиник, биллинга, entitlements и RAG KB (`OrganizationRagKbDocument.organization_id`). Кросс-клинический доступ админа явный: в `src/api/v1/clinic_scope.py` другая клиника разрешена только при совпадении `organization_id` **и** глобальной роли `owner` у «домашней» клиники; иначе **404/403**, чтобы не светить чужие тенанты.
- **HTTP-ответ при нарушении границы:** `src/api/v1/multitenancy_http.py` маппит `ClinicForbiddenError` в структурированный JSON (код `clinic_forbidden`, идентификаторы клиники/сущности, trace id).

**Масштаб реляционной модели**

- **~160 физических таблиц SQLAlchemy** по подсчёту строк **`__tablename__` по всему `src/`: 160** (включая связующие/вспомогательные; в одном модуле `omnichannel_chat_closure` — несколько имён таблиц).
- **160 модулей сущностей домена** в `src/domain/entities/` (без `__init__.py`): по сути соответствуют модели хранения.
- **98 файлов ревизий Alembic** в `alembic/versions/` (глубина эволюции схемы).

**RBAC**

- **Гранулярные коды прав:** в `src/application/rbac_matrix.py` — **`PermissionDef`: 49** уникальных кодов (примеры: `view_finance`, `manage_inventory`, `patients.pii.read`, `patients.medical.read` / `write`, операции Kanban по задачам, кампании лояльности, CRM и т.д.).
- **Принуждение к проверкам:** `RbacServiceImpl` (`src/application/services/rbac_service.py`) отдаёт **коды ролей и прав на пару `(user_id, clinic_id)`** через `RbacRepository`. На уровне роутеров проверки массовые: **300+ вхождений `require_permissions` / `user_has_any_permission` в `src/api/v1/routers`** (агрегированный подсчёт по модулям).
- **Персистентность:** сущности `permissions`, `roles`, `role_permissions`, `user_roles`, `user_permission_grant`, `rbac_audit_log` в `src/domain/entities/`.

---

## 2. Масштаб бэкенда и архитектуры

**HTTP-поверхность**

- **486 обработчиков маршрутов FastAPI** в `src/api/` по шаблону `@router.get|post|put|patch|delete|head|options(`.
- **94 модуля роутеров** в `src/api/v1/routers/` (включая общий `_admin_staff_common.py`).
- **565 Python-файлов** в `src/` (подсчёт `.py`).

**Стек (библиотеки)**

- Из `pyproject.toml`: **FastAPI**, **Starlette**, **Uvicorn**, **SQLAlchemy 2.x** + **asyncpg**, **Alembic**, **Pydantic v2**, **Redis** (`redis`, `aioredis`), **Celery** (extras с Redis), **httpx**, **prometheus-client**, **PyJWT**, **python-telegram-bot**, **boto3**, **cryptography**, **pyotp**.

**Фоновая обработка (Celery + Redis)**

- **Приложение Celery** `src/infrastructure/messaging/celery_app.py`: брокер и backend из настроек; **11 пакетов задач** в `include=[...]` (уведомления, AI, лояльность, интеграции владельца, экспорты, бэкапы, ERP, CRM, staff collab, биллинг платформы, domain outbox, сверка платежей).
- **Расписание beat (примеры критичных нагрузок):**
  - **Напоминания:** `notifications.run_reminders` каждые **900 с**.
  - **Генератор / менеджер AI-задач:** раз в сутки + почасовой обход клиник.
  - **Лояльность:** истекающие пакеты ежедневно; движок кампаний ежедневно.
  - **Коммуникации владельцу:** утренний брифинг 09:00 UTC; сводка AI-супервизора 20:00 UTC.
  - **Экспорты / уборка бэкапов:** `cleanup_old_exports_and_backups` в 04:00 UTC.
  - **ERP:** ночной пересчёт агрегатов **03:30 UTC**; выборочная сверка visit-revenue **05:15 UTC**.
  - **Staff collab:** напоминания календаря **каждые 300 с**.
  - **Биллинг платформы:** повтор провижининга **60 с**; истечение «зависших» интентов регистрации **3600 с**.
  - **Диспетчер outbox:** **`domain_outbox.dispatch_pending` каждые 30 с**.
  - **Сверка платежей:** reconcile local-pending YooKassa **каждые 600 с**.
- **Redis помимо Celery:** лимиты (`src/infrastructure/rate_limiter.py`), pub/sub омниканала (`src/infrastructure/realtime/omni_pubsub.py`), опциональный **fan-out вебчата между репликами** (канал `webchat:notify:{chat_id}` в `webchat_push_manager.py`).

**Транзакционный outbox**

- **Реализовано** в `src/application/services/domain_outbox_service.py`, сущность `DomainOutbox` (`src/domain/entities/domain_outbox.py`): **`INSERT ... ON CONFLICT DO NOTHING`** по **`dedup_key`** для идемпотентной постановки в очередь (успех платежа, провижининг SaaS-регистрации, жизненный цикл бронирования).
- **Доставка:** Celery-задача `domain_outbox.dispatch_pending` по расписанию; метрики включают `domain_outbox_dispatch_total`, gauge очереди, возраст самой старой записи, счётчик ошибок post-commit (в `src/core/metrics.py`).
- **Флаги** в настройках (см. `.env.example`): `DOMAIN_OUTBOX_PAYMENT_WEBHOOK_ENABLED`, `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED`, `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED`, лимиты батча и попыток диспетчера.

**Advisory locks и блокировки строк**

- **Сериализация слота врача:** `pg_advisory_xact_lock` через `src/application/booking_slot_advisory_lock.py` + ключи из `src/domain/booking_slot_policy.py` (используется из сервиса бронирования и CSV-импорта).
- **Обновление ERP:** `src/application/services/erp_refresh_lock.py` — **`pg_advisory_xact_lock`** с фиксированным namespace и ключом от `clinic_id`.
- **Лист ожидания:** в `waitlist_service.py` в докстринге указано `FOR UPDATE` для сериализации конверсии.

**Прочие «enterprise» паттерны данных**

- **Опциональная read-replica** для отчётных сессий (`get_db_reporting`, `DATABASE_REPLICA_URL`, `statement_timeout` в `src/infrastructure/database/base.py`).

---

## 3. Зрелость фронтенда и UI/UX

**Стек**

- **React 18.3**, **Vite 6**, **TypeScript ~5.6**, **React Router 6**, **Mantine 7**, **TanStack React Query 5**, **@dnd-kit**, **Vitest**, **Playwright** (`frontend/package.json`).

**Счётчики (`frontend/src`)**

- **151 файл `.tsx`** всего.
- **77 страничных компонентов** (под `pages/`, без сегментов пути `__tests__`).
- **24 примитива общего UI** в `shared/ui/`.
- **12 файлов `.tsx`** в `admin/components/` (drawer’ы сущностей, оболочки календаря и т.д.; остальной UI — в `admin/pages` и `shared/`).

**PWA**

- **Да:** `vite-plugin-pwa` + **Workbox** в `frontend/vite.config.ts` (manifest, иконки, скриншоты, shortcuts, `navigateFallback`, runtime caching); регистрация в `frontend/src/pwa/registerPwa.ts`. **В бэкенд `src` по grep WebSocket/`websocket` не найдены** (реалтайм — long-poll и Redis, не WS).

**Состояние и работа с API**

- **Серверное состояние:** **TanStack Query** (паттерны `useQuery` / `useMutation` в `frontend/src/hooks/`).
- **Псевдо-реалтайм:** **long-poll вебчата** с `asyncio.Event` в процессе + опциональный **Redis PUBLISH** (`src/application/services/webchat_push_manager.py`); омниканал — **Redis pub/sub** (`omni_pubsub`).

---

## 4. AI и внешние интеграции

**Реализация AI-ассистента**

- **Провайдер:** `AiClient` шлёт POST на **настраиваемый OpenAI-совместимый** `.../chat/completions` через **httpx** (`src/infrastructure/external_apis/ai_client.py`); URL, ключ, модель, таймаут из настроек.
- **Слой безопасности:** **`SafeAiClient`** оборачивает вызовы и прогоняет **`AiSanitizer`** по тексту сообщений до внешнего вызова (`src/infrastructure/external_apis/safe_ai_client.py`); отдельный **`src/core/ai_sanitizer.py`** (есть тесты, напр. `tests/core/test_ai_sanitizer.py`).
- **Омниканал-оркестрация:** крупный **`OmnichannelAIOrchestrator`** (`src/application/services/omnichannel_ai_orchestrator.py`) и **инструменты** в `src/application/ai/` (бронирование, CRM, задачи, реестр).
- **AI в админ-чате:** `ChatAiService` собирает контекст через `ChatService` и фабрику safe-клиента (`src/application/services/chat_ai_service.py`).

**RAG**

- **Да (уровень retrieval):** `OrganizationRagKbDocument` + сервис **`organization_rag_kb_service`**: поиск в границах **`organization_id`**; режимы **`ilike` (по умолчанию), `fts` (`plainto_tsquery` + `search_tsv`), `hybrid`** через `settings.rag_kb_search_mode`; явное **экранирование wildcards ILIKE** (`escape_ilike_user_fragment`). В коде отмечено, что векторный поиск — отдельная фаза (ссылка на **ADR-014**).

**Платежи и сторонние API (неполный список по коду)**

- **YooKassa:** `src/infrastructure/external_apis/yookassa_client.py`, модуль платежей платформы, вебхуки (роутеры `payments`, `platform_billing`).
- **Telegram:** `python-telegram-bot` + `telegram_sender.py`; исходящий диспетчер омниканала.
- **S3-совместимое хранилище:** `src/infrastructure/storage/s3_storage.py` (**boto3**).
- **Опционально AWS KMS:** `src/infrastructure/security/kms_data_key.py`.
- **Cloudflare Turnstile:** `turnstile_service.py`, на фронте `TurnstileWidget.tsx`.
- **SMTP:** `email_sender.py`.
- **OAuth:** `oauth_auth_service.py`, тесты роутера `auth`.

---

## 5. Наблюдаемость, QA и деплой

**Автотесты**

- **Сборка `pytest`: 803 теста** (`poetry run pytest tests/ --collect-only`).
- **Файлы `test_*.py` по папкам:** `tests/api` **82**, `tests/services` **34**, `tests/core` **31**, `tests/application` **15**, `tests/unit` **8**, `tests/e2e` **5**, `tests/deploy` **1** (в сумме **176 файлов**; остальное входит в общие 803).
- **Маркеры** (из `pyproject.toml`): `critical_path`, `regression_payments`, `regression_pd`, `regression_chats`, `security`, `redis_integration`; по **`critical_path` собирается 2 теста** (узкий merge-gate — возможно намеренно).
- **Фронт unit:** **27** файлов `*.test.ts(x)` в `frontend/src`.
- **Playwright в репозитории фронта:** **5** спек в `frontend/e2e/*.spec.ts`; в backend CI также **браузерные тесты Playwright** против **Vite preview** (см. `.github/workflows/backend-ci.yml` на ветке).
- **Типы тестов:** API FastAPI, сервисная интеграция, домен/приложение, security/observability, валидация JSON Grafana (`tests/core/test_grafana_dashboard_json.py`), YAML правил Prometheus (`tests/deploy/test_prometheus_alert_rules_yaml.py`).

**Стек наблюдаемости**

- **Prometheus:** `deploy/prometheus/prometheus.yml` + **`deploy/prometheus/dental_booking_alerts.yml`** — **36 правил с ключом `alert:`** (ERP, платежи, вебхуки, биллинг платформы, domain outbox, SOC, embed/RAG, patient auth, «застывший» логический бэкап и др.).
- **Grafana:** **4 JSON-дашборда** в `deploy/grafana/dashboards/`; провижининг datasource в `deploy/grafana/provisioning/`.
- **Alertmanager:** `deploy/alertmanager/alertmanager.yml` (+ пример Telegram).
- **Внутри приложения:** в `src/core/metrics.py` объявлены **115 `Counter`**, **18 `Histogram`**, **8 `Gauge`** (**141 инструмент** только в этом модуле); нормализация пути для кардинальности метрик — там же.

**Деплой и CI/CD**

- **Docker Compose:** `docker-compose.yml` — **Postgres 16** (`max_connections=200`), **Redis 7**, **job миграций**, образы приложения через `BACKEND_IMAGE` / `FRONTEND_IMAGE`, воркеры/beat по файлу; опциональный **профиль observability** в `.env.example`.
- **Образы:** корневой `Dockerfile` (бэкенд) + `frontend/Dockerfile`.
- **GitHub Actions:** **9 workflow-файлов** в `.github/workflows/`: backend-ci, build-and-test-entitlements, critical-path-gate, release-gate, docker-hub-publish, docker-images-build-verify, documentation-markdown-links, dr-restore-drill, security-trivy.
- **Jenkins / GHCR:** в репозитории задокументирован как **корпоративный** путь (`Jenkinsfile`, `AGENTS.md`, `CI_CD.md`).

---

## Позиционирование для покупателя (факты)

Кодовая база выглядит как **слоистый модульный монолит** (FastAPI + SQLAlchemy + Celery) с **явными границами мультитенантности** (`clinic_id` / `organization_id`), **десятками гранулярных прав RBAC**, **сотнями HTTP-операций**, **~160 реляционными таблицами**, **транзакционным outbox + advisory locks PostgreSQL**, **широким покрытием фоновых задач**, **артефактами Prometheus/Grafana/Alertmanager** и **803 автоматическими тестами**, включая API, сервисы, security, проверки артефактов наблюдаемости, а также unit и Playwright на фронте.

При необходимости можно вынести метрики в **слайды (одна цифра на слайд)** или **согласовать определение «таблица в проде»** (исключить тест-only модели, если такие появятся).
