# Черновик границы API: `/platform/*` vs `/admin/*` (Фаза 1a)

> **Статус:** Phase 1a черновик для согласования с [backend/api_layer.md](../backend/api_layer.md) и OpenAPI. **Не** смешивать JWT Основателя и админа клиники (МП §19 п.3).  
> **Полное архитектурное моделирование срезов E1–E6 (FE+BE, прод):** [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md).

## Текущее состояние (факт кода)

| Префикс | Назначение | Аутентификация |
|---------|------------|----------------|
| `/api/v1/platform/billing/webhooks/yookassa` | Webhook контура **B** (YooKassa) | Секрет `X-Platform-Billing-Webhook-Secret`, не Bearer |
| `/api/v1/platform/auth/login` | Выдача JWT Основателя по **email + паролю** (1a-E2) | Без Bearer; per-IP / per-email rate limit; ответ содержит `access_token` с `type=platform_founder`, `sub` = UUID строки **`platform_founder_users`**. |
| `/api/v1/platform/internal/health` | Проверка контура JWT Основателя (Phase 1a) | Bearer JWT: **`type=platform_founder`**, `sub` = UUID **активного** пользователя в **`platform_founder_users`**; подпись **`PLATFORM_FOUNDER_JWT_SECRET`** (пусто → fallback на `JWT_SECRET_KEY` **только dev/staging**). **`APP_ENV=production`** и секрет пустой: маршрут **503** (`platform_founder_jwt_not_configured`), приложение в целом **стартует**. Per-IP rate limit (Redis), см. `rate_platform_founder_auth_*`. **Недопустимо:** валидный JWT с `sub`, отсутствующим в БД или с `is_active=false` — **403**. |
| `/api/v1/platform/internal/signup-intents/{id}/owner-invite-token` | Выпуск/ротация одноразового токена приглашения владельца после провижининга B | Только Bearer **`platform_founder`**; токен передаётся владельцу по защищённому каналу (до email-автоматизации — операционная процедура). |
| `/api/v1/public/platform/owner-invite/accept` | Установка пароля владельца по одноразовому токену | Без JWT; per-IP rate limit (`rate_platform_owner_invite_accept_*`). |
| `/api/v1/admin/...` | Операции **тенанта** (клиника) | JWT админа (`type=admin` в payload логина), `current_admin.clinic_id` |
| `/api/v1/owner/...` | Омниканал под префиксом owner | Фактически тот же админ клиники — [OWNER_API_SEMANTICS_U005_DRAFT.md](./OWNER_API_SEMANTICS_U005_DRAFT.md) |

### JWT: Основатель vs тенант (минимальная спека)

| Claim / поле | Админ клиники | Пациент | Основатель платформы |
|--------------|---------------|---------|----------------------|
| Распознавание | `type=admin` (через `admin/auth/login`) | `role=patient` | **`type=platform_founder`** |
| `sub` | UUID `AdminUser` | UUID `Patient` | UUID строки **`platform_founder_users`** (1a-E2); bootstrap через `python -m src.scripts.create_platform_founder_user` |
| Ключ подписи | `JWT_SECRET_KEY` | `JWT_SECRET_KEY` | **`PLATFORM_FOUNDER_JWT_SECRET`**; вне **production** при пустом значении — fallback на `JWT_SECRET_KEY`; в **production** при пустом — только **503** на `/platform/internal/*` (без fallback) |
| **`iss` (1a-E6)** | `JWT_ISSUER_TENANT` (default `dental-booking-tenant`) | то же | **`JWT_ISSUER_PLATFORM`** (default `dental-booking-platform`) |
| **`aud` (1a-E6)** | `JWT_AUDIENCE_ADMIN` (`dental-booking-admin`) | `JWT_AUDIENCE_PATIENT` (`dental-booking-patient`) | access: **`JWT_AUDIENCE_PLATFORM_FOUNDER`** (`platform-internal`); MFA step: **`JWT_AUDIENCE_PLATFORM_FOUNDER_MFA`** (`platform-mfa-step`) |
| Зависимость FastAPI | `get_current_admin` / `require_permissions` | `get_current_patient` | **`get_current_platform_founder`** (`dependencies.py`) |

**Dual-read (cutover):** пока `JWT_LEGACY_ALLOW_MISSING_ISS_AUD=true`, принимаются старые токены **без** пары `iss`+`aud` (и без «половинчатых» claims). После выдачи всех клиентов — **false** в prod. Неверный `iss`/`aud` → **`JwtClaimValidationError`** → HTTP **401** с `code`: `invalid_token_issuer` \| `invalid_token_audience` \| `invalid_token_claims` (тенант и `/platform/internal/*` для Основателя).

Маршруты с `get_request_context` по-прежнему принимают только **admin** и **patient**; токен `platform_founder` на такие пути даст **401** «Недопустимый тип токена» — это ожидаемо до появления единого диспетчера.

## Целевое расширение (после Фазы 1a+, без даты)

- **`/api/v1/platform/...`** (кроме публичного webhook): только **principal Основателя** (отдельный issuer/claims), audit platform-уровня.
- **Запрет:** читать/писать platform-таблицы (`platform_signup_intents`, платежи B, будущие platform-user) из обработчиков с `get_current_admin` без явного барьера и ревью ARCH.
- **Публичный периметр тенанта:** [U-011](../UNRESOLVED_AND_CONFUSION_LOG.md) — анонимный список клиник сужен (slug + legacy single-tenant), PII scrub, rate limit по IP; GET по id без admin — 404.

## Приёмка среза 1a-E1 (спека)

- Зафиксированы границы `/platform/auth/login` vs `/platform/internal/*` vs webhook B (секрет, не Bearer).
- Подтверждено: `sub` в founder-JWT обязан резолвиться в БД (1a-E2); ручной mint без строки в БД — только для аварийного OPS и не для штатных интеграций.
- U-005: без изменений — не расширять `/owner/*` до закрытия [OWNER_API_SEMANTICS_U005_DRAFT.md](./OWNER_API_SEMANTICS_U005_DRAFT.md).

## Следующие шаги @DEV

1. ~~Логин Основателя / привязка `sub` к строке в БД~~ — **1a-E2 (реализовано в коде)**; далее 2FA (МП §9) — **1a-E3**.
2. Расширить OpenAPI описаниями ответов для `platform-internal` и контрактом webhook B.
