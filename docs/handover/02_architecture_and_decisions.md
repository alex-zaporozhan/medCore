# Архитектура и принятые решения

Документ фиксирует структуру системы так, как она выражена в коде. Детальные обоснования и эволюция решений — в `docs/adr/` (индекс: `docs/adr/README.md`).

## Модульный монолит и слои

Один развёртываемый backend-процесс (FastAPI) плюс отдельные процессы Celery worker/beat. Зависимости направлены от HTTP-слоя к домену; инфраструктура реализует контракты домена.

| Слой | Расположение | Роль |
|------|----------------|------|
| HTTP / API | `src/api/v1/routers/`, подключение в `src/api/v1/router.py` | Маршруты, зависимости, RBAC-обвязка (`src/api/v1/dependencies.py`), маппинг в DTO. |
| Application | `src/application/services/`, `src/application/dto/`, `src/application/events/` | Бизнес-правила, оркестрация, публикация событий. В `application/services/` — порядка **70** файлов с суффиксом `service` в имени плюс вспомогательные модули (локи, движки, кэш-обёртки). |
| Domain | `src/domain/entities/`, `src/domain/interfaces/` | ORM-модели и интерфейсы репозиториев; порядка **160** файлов сущностей. |
| Infrastructure | `src/infrastructure/database/`, `storage/`, `messaging/`, `external_apis/`, `realtime/` | Реализации репозиториев, Celery-задачи, внешние клиенты, Redis/S3. |

Точка входа приложения: `src/main.py` (lifespan, middleware, метрики, регистрация обработчиков in-process EventBus).

## События: in-process шина и outbox

- **In-process EventBus** — `src/application/events/event_bus.py`; регистрация обработчиков в `src/main.py` (CRM, ERP, loyalty, tasks, marketing attribution). Подходит для побочных эффектов в том же процессе, но не заменяет гарантии доставки между процессами.
- **Transactional outbox** — для устойчивой доставки после коммита (в т.ч. платежные вебхуки и провижининг платформы). Реализация и флаги: `src/application/services/domain_outbox_service.py`, задачи `src/infrastructure/messaging/tasks/domain_outbox_tasks.py`, ADR-009 в `docs/adr/ADR-009-async-outbox-event-delivery.md`. Включение по переменным окружения — см. `.env.example` (`DOMAIN_OUTBOX_*`).

## Мультитенантность и доступ

- **Клиника** — основной тенант: `clinic_id` в сущностях и в JWT административного контура (`type=admin` в токене, см. `src/api/v1/routers/admin_auth.py`).
- **Организация** — уровень сети/холдинга: `organization_id` на админ-пользователе и в ряде сущностей; биллинг и entitlements завязаны на организацию (роуты и сервисы `platform_*`, `organization_*`).
- **RBAC** — канонический список прав и ролей: `src/application/rbac_matrix.py` (сейчас порядка **49** атомарных кодов прав в `PERMISSIONS`). Изменение матрицы должно сопровождаться миграциями и синхронизацией инвентаря эндпоинтов: `scripts/audit_rbac_endpoints.py`, снимок `documentation/rbac_router_permissions.txt`, тест `tests/application/test_sec_rbac_router_permissions_inventory.py`.
- **Разделение ответов при отсутствии прав** — в ряде сценариев используется 404 вместо 403 против перечисления чужих идентификаторов (см. обзор в `docs/product_state/ARCHITECTURE_FROM_CODE.md` и тесты изоляции в `tests/api/`).

## Идентичность и JWT

Три основных HS256-контура с разными claim и политиками TTL:

- Администратор клиники — `type=admin`, отдельный TTL (`jwt_access_token_expire_minutes_admin`).
- Пациент — отдельный поток в `src/api/v1/routers/auth.py` / `src/application/services/auth_service.py`.
- Основатель платформы — `type=platform_founder`, отдельный секрет `PLATFORM_FOUNDER_JWT_SECRET` в production (`src/core/security.py`, проверки при старте в `src/main.py`).

Issuer/audience для тенантных токенов настраиваются через `JWT_ISSUER_TENANT`, `JWT_AUDIENCE_*` (см. `.env.example`).

## Платежи и вебхуки

- **Контур A** — пациентские платежи; вебхук и секрет `PATIENT_PAYMENT_WEBHOOK_SECRET`, лимиты по IP — в `.env.example`.
- **Контур B** — подписка/биллинг платформы; `PLATFORM_BILLING_WEBHOOK_SECRET`, отдельные rate limits.
- На старте приложения выполняется проверка различия секретов и обязательных политик для production: `src/core/payment_webhook_governance.py`, вызовы из `src/main.py`. Подробности контрактов — ADR-011, ADR-015, `docs/adr/README.md`.

## Конкурентность записи в расписание

Сериализация мутаций на одном слоте врача — **PostgreSQL advisory transaction lock** по паре ключей из даты/времени/врача: `src/application/booking_slot_advisory_lock.py`, `src/domain/booking_slot_policy.py`, использование в `src/application/services/booking_service.py` и импорте CSV (`csv_import_service.py`). Отдельный advisory-лок для пересчёта ERP: `src/application/services/erp_refresh_lock.py`.

## Отчётность и нагрузка на БД

- Опциональная **read replica** для части GET-отчётов: `database_replica_url`, `db_reporting_statement_timeout_ms` в `src/core/config.py`; поведение сессий — `src/infrastructure/database/base.py`, ADR-005 зафиксирован в `docs/adr/README.md` (якоря в коде).
- Кэш JSON для ERP dashboard — Redis, TTL и флаги в настройках (`erp_dashboard_cache_*`).

## Frontend как одно SPA

Один бандл Vite покрывает публичные, пациентские, админские и платформенные зоны; маршруты в `frontend/src/`. Обращение к API — префикс `/api` (прокси в dev, см. `frontend/vite.config.ts` и `frontend/src/api/client.ts`).

## Масштабирование (как заложено в архитектуре)

- Горизонтальное добавление экземпляров API при общем Redis и идемпотентных вебхуках/outbox.
- Независимое масштабирование Celery workers.
- Реплика для тяжёлых чтений и лимиты времени запроса на reporting-сессиях.
- Вынос отдельных bounded contexts в отдельные сервисы возможен точечно; границы частично описаны в ADR (например ADR-013 commerce).

## Наблюдаемость (кратко)

Метрики Prometheus и правила алертов лежат в `deploy/prometheus/` (в т.ч. порядка **36** правил с ключом `alert:` в `dental_booking_alerts.yml`). Дашборды Grafana — JSON в `deploy/grafana/dashboards/` (**4** файла), провижининг в `deploy/grafana/provisioning/`. Подробнее: `deploy/grafana/README.md`, `documentation/OBSERVABILITY.md` при наличии.
