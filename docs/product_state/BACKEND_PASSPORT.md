# Backend-паспорт (только факты из кода)

> **Версия:** 2026-04-10 (@QA_ARCH фаза 3: актуальный `router.py`, Redis, backup, outbox)  
> **Источник истины:** `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `src/main.py`, `src/core/config.py`, `src/api/v1/router.py`, дерево `src/`, `alembic/versions/`, `tests/`.  
> **Системная картина (схемы):** [`ARCHITECTURE_FROM_CODE.md`](./ARCHITECTURE_FROM_CODE.md) §10–16 · навигация S: [`RAG_NAVIGATION_S_LAYER.md`](./RAG_NAVIGATION_S_LAYER.md).

---

## 1. Назначение и стек

| Параметр | Значение в репозитории |
|----------|-------------------------|
| Язык | Python ^3.11 |
| HTTP framework | FastAPI (^0.135), Starlette |
| ASGI server | Uvicorn (^0.34) |
| ORM | SQLAlchemy 2.x |
| Драйвер БД | asyncpg |
| Миграции | Alembic |
| Валидация / settings | Pydantic 2, pydantic-settings |
| Кэш / брокер | Redis 5, aioredis 2 |
| Фоновые задачи | Celery 5 + Redis broker/result |
| Крипто / пароли | cryptography, passlib[bcrypt] |
| JWT | PyJWT |
| HTTP client | httpx |
| Telegram | python-telegram-bot |
| Объектное хранилище | boto3 (S3-совместимое) |

Описание пакета в Poetry: «MVP системы записи клиентов в стоматологии» — фактически код покрывает существенно больше доменов (см. роутеры и сервисы ниже).

---

## 2. Точка входа и HTTP-поверхность

**Файл:** `src/main.py`

- Приложение: `FastAPI(title=settings.app_name, version="0.1.0", lifespan=...)`.
- API монтируется: `app.include_router(api_router, prefix=settings.api_v1_prefix)`; если `api_v1_prefix != "/api/v1"`, роутер дублируется ещё с префиксом `/api/v1`.
- **CORS:** `CORSMiddleware`, origins из `settings.cors_origins_list`.
- **Trace:** middleware выставляет `X-Trace-Id` (генерация UUID при отсутствии заголовка).
- **Метрики:** middleware длительности запросов → Prometheus histogram (исключая `/metrics`, `/health`, `/health/replica`).
- **Ошибки:** единый envelope для `HTTPException` и `RequestValidationError` (`detail`, `code`, опционально `trace_id`, для 422 — `errors`); глобальный handler на необработанные исключения — 500 без утечки стека клиенту.
- **OpenAPI UI:** в `production` `docs_url` и `redoc_url` = `None`; в иных окружениях `/docs` и `/redoc`.
- **Lifespan:** регистрация обработчиков event bus: `lead`, `erp`, `loyalty`, `tasks`, `marketing_attribution`; assert’ы платёжных секретов и governance (`payment_webhook_governance`); при shutdown — `close_redis`.

**Корневые маршруты приложения (вне `api_router`):**

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/health` | Liveness |
| GET | `/health/s3` | Проверка S3 (медфайлы) |
| GET | `/health/replica` | Проверка reporting DSN / lag реплики |
| GET | `/metrics` | Prometheus |

---

## 3. API v1: состав роутеров

**Файл:** `src/api/v1/router.py` — единая сборка `api_router`.

- **Количество** вызовов `api_router.include_router(...)` в этом файле: **92** (проверка: grep `^api_router\\.include_router` по `router.py`). Порядок подключения задаёт приоритет пересечений путей при совпадении шаблонов.
- Полный перечень импортов и цепочка `include_router` — только в исходнике `router.py` (строки ~103–194).
- **Дополнения к ранним спискам паспорта:** в дереве подключены также (среди прочих) `platform_founder_auth`, `platform_billing`, `platform_internal`, `public_embed`, `public_platform_catalog`, `public_platform_signup`, `public_platform_owner_invite`, `admin_embed`, `admin_rag_kb`, `admin_organization_data_export`, `admin_organization_profile`, `admin_commerce`, `admin_commerce_network`, `admin_crm_import`, `admin_payroll`.
- Вспомогательные модули без собственного `include_router` в `router.py`: например `_admin_staff_common.py`.

**Автогенерация поверхности методов:** `python scripts/generate_router_surface_docs.py` → `docs/product_state/generated/router_surface/INDEX.md` (порядок согласуется с `include_router`).

---

## 4. Авторизация, контекст, редакция

**Файлы:** `src/api/v1/dependencies.py`, `src/core/security.py`, `src/core/edition.py`, `src/api/v1/routers/admin_auth.py` (строгий `get_current_admin`).

- **Пациент:** Bearer JWT, audience `jwt_audience_patient`, поле `role=patient`, загрузка `Patient` из БД (`get_current_patient`).
- **Админ:** JWT `type=admin`, audience `jwt_audience_admin`, опциональная валидация `iss`/`aud` (`JwtClaimValidationError` → 401 с кодом). Загрузка `AdminUser` + проверка org billing revoked при наличии `organization_id`.
- **Основатель платформы:** отдельные роутеры и секрет `PLATFORM_FOUNDER_JWT_SECRET` (в prod без секрета — отдельная политика для platform-маршрутов; см. `security.py` `is_platform_founder_jwt_configured`).
- **RequestContext:** `get_request_context` собирает admin/patient/anon; RBAC через `RbacServiceImpl`.
- **Зависимость** `require_permissions(*codes)` — для админского контура.
- **Enterprise vs Box:** `require_crm_enterprise_edition()` → 403 `box_forbidden` при edition `box`/`basic`.

Схемы потоков: [`ARCHITECTURE_FROM_CODE.md`](./ARCHITECTURE_FROM_CODE.md) §10.

---

## 5. Конфигурация окружения (обзор полей)

**Файл:** `src/core/config.py` (часть полей; полный список — в файле).

- Обязательные: `secret_key`, `jwt_secret_key`, `database_url`.
- БД: пул, опционально `database_replica_url`, таймауты reporting, порог lag для `/health/replica`.
- Redis: URL, пул, TTL кэшей ERP dashboard / staff directory.
- Rate limits: auth SMS/code, admin login, AI, omni send, staff/patient chat, staff chat room.
- Turnstile (опционально).
- YooKassa, Telegram, SMS SMC, OAuth VK/Yandex, SMTP.
- Celery broker/backend.
- Пути и лимиты staff chat вложений; S3 endpoint/bucket/keys/prefixes/presign TTL для медфайлов и аватаров; политика medical download token (UA/IP, trusted proxies).
- Логирование: уровень, формат (json), `log_mask_pii`.
- AI provider URL/key/model/timeout; флаги Telegram-уведомлений omni AI.
- Флаги ERP: чтение из aggregate, per-report overrides.
- `metrics_enabled`, `api_v1_prefix`, `app_env`, `debug`, CORS, `form_link_base_url`, и др.

---

## 6. Слои кода backend

| Каталог | Роль |
|---------|------|
| `src/api/v1/` | HTTP: роутеры, схемы ответов, зависимости |
| `src/application/services/` | Прикладная логика (**90** файлов `.py` в каталоге на 2026-04; из них **69** с суффиксом `*_service.py`, остальные — кэш, ERP-read, биллинг платформы, state machine и т.п.) |
| `src/application/dto/` | DTO между слоями |
| `src/application/events/` | Event bus, доменные события, обработчики (lead, erp, loyalty, tasks, marketing) |
| `src/application/` | `rbac_matrix.py` — канон кодов permissions и привязка к ролям (синхронизация с миграциями — по комментариям в файле) |
| `src/domain/entities/` | ORM-сущности домена (**160** файлов `.py` в каталоге, включая `__init__.py`) |
| `src/domain/interfaces/repositories/` | Контракты репозиториев |
| `src/infrastructure/database/` | Реализации репозиториев, `base.py` (сессии, reporting) |
| `src/infrastructure/messaging/` | Celery app, задачи: notifications, ai_tasks, loyalty_tasks, owner_integrations, export_tasks, backup_tasks, erp_tasks, crm_tasks, staff_collab_tasks |
| `src/infrastructure/storage/` | S3 storage |
| `src/infrastructure/realtime/` | Omni pubsub |
| `src/infrastructure/external_apis/` | YooKassa, SMS, email, AI client, Telegram |
| `src/core/` | config, logging, metrics, security, edition, messages, sanitizers, и т.д. |
| `src/scripts/` | Утилиты, в т.ч. `seed_demo_data.py` |

**Инвентарь модулей:** канонический список — каталог `src/application/services/` (все `*.py`). Дополнения после среза списка в паспорте: `commerce_import_job_service`, `commerce_store_service`, `embed_public_ai_service`, `organization_entitlement_access`, `patient_entry_clinic`, `platform_billing_access`, `platform_billing_service`, `platform_catalog_service`, `platform_tariff_payment_gate`, `platform_yookassa_payment`, `rag_kb_audit_service`, `domain_outbox_service` и др.; при расхождении — **glob по каталогу**, не этот абзац.

---

## 7. Фоновые задачи (Celery)

**Файл:** `src/infrastructure/messaging/celery_app.py`

- Уведомления пациенту: `send_with_fallback` различает реальную отправку (SMS/Telegram/email) и ветку **log-only** без каналов; в БД для последнего используется статус `skipped_no_channel`, а не `sent` (P1-5 / QA_ARCH). Задачи: `notifications.py`, `loyalty_tasks.py`; recall: `recall_service.run_campaign` + поле `skipped_no_channel` в JSON ответа run-кампании.
- Периодические задачи (beat): напоминания (15 мин), AI task generator (сутки), AI task manager (час), проверка истекающих пакетов лояльности, движок кампаний лояльности, owner morning brief (09:00 UTC), AI supervisor summary (20:00 UTC), cleanup exports/backups (04:00 UTC), ERP aggregates nightly (03:30 UTC), ERP visit revenue parity sample (05:15 UTC), staff calendar reminders (5 мин).
- При отсутствии установленного пакета `celery` используется заглушка для импорта (см. код — важно для тестовых сред).

---

## 8. Миграции БД

**Каталог:** `alembic/versions/` — **91** файл `.py` ревизий (включая merge-heads; число по факту дерева на 2026-04). Начальная схема: `03e4d2406cdb_schema_v2_initial.py`; далее эволюция: CRM/loyalty/family, ERP vitrines, RBAC, staff collab, omnichannel, medical files, tasks/kanban, lead logs, platform billing, embed, commerce, domain_outbox, RAG KB и т.д.

---

## 9. Тесты

**Каталог:** `tests/` — десятки модулей: `api/`, `services/`, `security/`, `e2e/` (Playwright), `core/`, `application/`, `unit/`. Маркеры pytest в `pyproject.toml`: `regression_payments`, `regression_pd`, `regression_chats`, `security`.

---

## 10. Деплой backend в compose

**Файл:** `docker-compose.yml`

- Сервис `backend`: образ из `Dockerfile`, команда `uvicorn src.main:app`, порт 8010→8000, зависимости от `migrations`, `db`, `redis`, volume `staff_uploads` для вложений staff chat.
- Отдельно: `celery`, `celery-beat`, одноразовый `migrations` (`alembic upgrade head`).

---

## 11. Инвентарь RBAC и поверхность роутеров (автоматизация)

| Артефакт | Назначение |
|----------|------------|
| `scripts/audit_rbac_endpoints.py` | Собирает коды из `require_permissions(...)` в `src/api/v1/routers/*.py`. |
| `docs/product_state/baselines/rbac_router_permissions.txt` | Зафиксированный список (одна строка — один код). `--write` перезаписывает; `--check` сравнивает с кодом. Тест: `tests/application/test_sec_rbac_router_permissions_inventory.py`. |
| `scripts/generate_router_surface_docs.py` | Статический разбор методов/префиксов по модулям; вывод: `docs/product_state/generated/router_surface/INDEX.md` (порядок = `include_router` в `router.py`). |

---

## 12. Внешние интеграции (по наличию в коде)

Заглушки и клиенты присутствуют для: **YooKassa**, **Telegram**, **SMSC**, **SMTP**, **OAuth (VK/Yandex)**, **S3-совместимое хранилище**, **HTTP AI provider** (base URL + key в config). Фактическая «включённость» определяется переменными окружения в `src/core/config.py`, а не документацией.

---

## 13. Redis (кэш, лимиты, служебные ключи)

Канон ключей и сценариев: [`ARCHITECTURE_FROM_CODE.md`](./ARCHITECTURE_FROM_CODE.md) §11. Код: `erp_report_cache.py` (`erp:rpt:v1:…`), `staff_directory_cache.py` (`staff:dir:v1:…`), `backup_tasks.py` / `admin_vault.py` (`backup:status:…`), `rate_limiter.py` + вызовы в dependencies и публичных роутерах, `auth_service` / `auth` router для OTP/state.

---

## 14. Логический backup (не pg_dump)

Celery-задача `backup_tasks.run_full_backup`: JSON-экспорт по клинике, статус в Redis, файлы на диске, HTTP API в `admin_vault`. Очистка старых файлов — `export_tasks.cleanup_old_exports_and_backups`. Кластерный backup БД — вне этого паспорта (OPS / DR runbook).

---

## 15. Domain outbox

Таблица `domain_outbox`, флаги `DOMAIN_OUTBOX_*` в settings, post-commit dispatch в `get_session_payment_webhook` / `get_session_booking_domain_outbox`, метрики в `metrics.py`, Celery-диспатч в `domain_outbox_service`. Детали: [`ARCHITECTURE_FROM_CODE.md`](./ARCHITECTURE_FROM_CODE.md) §14.

---

## 16. Reporting session и replica

`get_reporting_session` → `get_db_reporting()` при наличии `database_replica_url`; иначе тот же пул, что primary. См. `base.py`, `GET /health/replica`.

---

**Якорные файлы для навигации:** `src/main.py`, `src/api/v1/router.py`, `src/core/config.py`, `src/api/v1/dependencies.py`, `src/core/security.py`, `src/infrastructure/database/base.py`, `src/infrastructure/messaging/celery_app.py`, `src/application/services/domain_outbox_service.py`.
