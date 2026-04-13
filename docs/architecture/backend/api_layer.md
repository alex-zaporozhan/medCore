# Слой API (FastAPI v1)

Точка сборки: `src/api/v1/router.py`. Роутеры лежат в `src/api/v1/routers/` (около 79 Python-файлов, с `_admin_staff_common` и т.п.).

## Назначение

HTTP-граница: Pydantic, зависимости FastAPI, вызовы `application.services`, коды ответов. Агрегирование всех подроутеров — в `router.py` через `include_router`.

## Как это работает (паттерн запроса)

1. **Сборка дерева:** `src/api/v1/router.py` создаёт пустой `APIRouter()` и последовательно вызывает `include_router(...)` для каждого модуля из `src/api/v1/routers/`. У каждого файла свой `router` с собственным `prefix` (часто `/admin/clinics`, `/v1/patient`, и т.д.) — итоговый путь = префикс приложения (`settings.api_v1_prefix`) + prefix роутера + путь эндпоинта.
2. **Инъекция зависимостей:** типичный админский эндпоинт объявляет `session: AsyncSession = Depends(get_session)`, `current_admin: AdminUser = Depends(get_current_admin)` или цепочку RBAC: `_perm_ctx: AdminContext = Depends(require_permissions("..."))` (`src/api/v1/dependencies.py`). `get_session` проксирует в `get_db()`: одна транзакция на запрос (commit при успехе).
3. **Контекст и права:** `get_request_context` разбирает Bearer: для `type=admin` подгружает `AdminUser`, затем через `RbacServiceImpl.get_rbac_info_for_user` наполняет `RequestContext.permissions`. `require_permissions` допускает только админа и проверяет пересечение множеств permissions. Для пациента `get_current_patient` проверяет claim `role=patient` и наличие строки в БД.
4. **Вызов логики:** эндпоинт либо собирает сервис вручную (`TaskRepositoryImpl(session)` → `TaskService(repo)`), либо вызывает уже готовый сервисный метод; возвращает Pydantic `response_model` или сырой dict/list.
5. **SaaS entitlement-gate (Phase 1c):** опциональные модули (tasks, marketing, CRM и др.) — `require_entitlement` на `APIRouter` ([`entitlement_dependencies.py`](../../../src/api/v1/entitlement_dependencies.py)); инвентарь — [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md). Legacy: при отсутствии строк в `organization_entitlements` enforcement не режет доступ.
6. **Ответы об ошибках:** роутер обычно бросает `HTTPException`; формат для клиента нормализует `http_exception_handler` в `main.py` (строка или dict `detail` + машинный `code`). **Долг QA_ARCH:** единый регистр стабильных `code` (предпочтительно lower в JSON) и явный контракт 403 для гейтов — [arch_plan/04_PHASE_1C_ENTITLEMENTS.md](../arch_plan/04_PHASE_1C_ENTITLEMENTS.md) B2/B4, [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md), [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](../arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) §28.

## Зоны по префиксам модулей

- **Публичное:** `public_services`, `public_marketing`, `public_doctor_profiles`.
- **Пациент:** `patients`, `patient_chat`, `patient_forms`, `patient_loyalty`, `patient_notification_settings`.
- **Админка:** множество `admin_*` (расписание, финансы, CRM, задачи, омниканал, AI, RBAC и др.).
- **Омни «owner» в URL (не отдельная роль JWT):** `owner_omni_channels`, `owner_omni_ai_settings`, `owner_omni_audit` — фактически **`get_current_admin`** и область **`current_admin.clinic_id`** как business account (см. `src/api/v1/routers/owner_omni_channels.py`). Не путать с «владельцем платформы SaaS». Отдельно: `integrations_gateway`.
- **Общие:** `auth`, `bookings`, `schedule`, `payments`, `reports`, `config`, `stickers`, `csv_sync`, `doctors`, `services`, `clinics`, `ai_agent`. **Клиники (U-011):** без **admin** JWT — `GET /api/v1/clinics/{id}` → **404**; `GET /api/v1/clinics` — **rate limit** по IP, **PII scrub**, только клиники с **`clinic_slug`**, кроме режима **ровно одна** активная клиника в БД (legacy). С Bearer админа — полный список как раньше (`frontend/src/api/client.ts` подставляет токен на `/v1/clinics`).
- **Платформа SaaS (контур B, отдельно от пациентских платежей):** `platform_billing` — `POST /platform/billing/webhooks/yookassa`; секрет `X-Platform-Billing-Webhook-Secret` / `PLATFORM_BILLING_WEBHOOK_SECRET` (не смешивать с `/payments/webhook`). **Оператор платформы (Фаза 1a):** `platform_internal` — `GET /platform/internal/health` с Bearer JWT `type=platform_founder`; в non-production при пустом `PLATFORM_FOUNDER_JWT_SECRET` допускается fallback на `JWT_SECRET_KEY`, в **production** без секрета маршрут **503**, остальной API работает. Черновик: [specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](../specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md).

Полный список импортов и порядок подключения — только в `src/api/v1/router.py`.

## RBAC и edition

Проверки прав размазаны по роутерам; матрица и тесты: `src/application/rbac_matrix.py`, `tests/application/test_rbac_matrix_w7.py`, инвентарь `docs/product_state/baselines/rbac_router_permissions.txt`.

## Статус

- Покрытие доменами: реализовано (широкая поверхность).
- Документирование каждого эндпоинта здесь: не цель; OpenAPI при не-production `app_env`.

## Непонятное

Точная роль на каждый маршрут без чтения файла роутера не фиксируется; при сомнениях — OpenAPI или тест в `tests/api/`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** при появлении platform-operator без отдельного guard все админские роутеры останутся опасной поверхностью; сейчас такого типа пользователя нет (см. [INDEX.md](../INDEX.md)).
- **Средние риски:** имя префикса `/owner/*` вводит в заблуждение относительно фактического `AdminUser` + `clinic_id` ([UNRESOLVED U-005](../UNRESOLVED_AND_CONFUSION_LOG.md)).
- **Формально / недоделано:** RBAC размазан по файлам; полная матрица покрытия только через инвентарь + pytest.
- **Рекомендуемые доработки:** явные зависимости-фабрики для «network scope» если продукт требует кросс-клинический omni без смены клиники в UI.

### Соответствие фактам (проверка)

- Паттерн `Depends`, `require_permissions`, `get_request_context` — по `src/api/v1/dependencies.py`.
- Семантика `owner_omni_*` — по `owner_omni_channels.py` (list/create используют `current_admin.clinic_id`).

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** рассинхрон `clinic_id` в path и JWT при ошибках UI или подмене storage; webhook-эндпоинты **A и B** должны быть идемпотентны ([U-006](../UNRESOLVED_AND_CONFUSION_LOG.md)); контур B — `tests/api/test_platform_billing.py`.
- **Что усилить:** contract-тесты OpenAPI для платежей и критичных admin POST.
- **С нуля:** отдельный router guard для platform-operator при появлении продукта.
- **БД:** не в слое роутера; косвенно — фильтры по `clinic_id` в сервисах.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) (§2.3, §2.1).
