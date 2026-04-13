# QA_REPORT — срез 1a-E6 (JWT `iss` / `aud`, отдельный issuer платформы)

> **Эпик:** [STREAM_1A_PLATFORM_EPICS.md](../architecture/arch_plan/STREAM_1A_PLATFORM_EPICS.md) **1a-E6**  
> **Модель:** [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../architecture/arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md) §2.2, §3.6  
> **Долг:** [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) **1a-F4** → **done**

## Реализация @DEV (код)

| Компонент | Изменение |
|-----------|-----------|
| `src/core/config.py` | Поля `jwt_issuer_tenant`, `jwt_audience_admin`, `jwt_audience_patient`, `jwt_issuer_platform`, `jwt_audience_platform_founder`, `jwt_audience_platform_founder_mfa`, `jwt_legacy_allow_missing_iss_aud` |
| `src/core/security.py` | Mint: `iss`+`aud` на tenant и founder access/MFA; verify: `parse_access_token(..., expected_audience=…)`, `parse_tenant_access_token_for_request_context`, `parse_platform_founder_*`; исключение `JwtClaimValidationError` |
| `src/api/v1/dependencies.py` | Founder: негативы iss/aud → **401** + счётчик `platform_founder_jwt_reject_total{reason}` |
| `src/api/v1/routers/admin_auth.py` | Парсинг admin JWT с ожидаемой audience |
| `src/application/services/oauth_auth_service.py` | Исправлен `expires_delta` для patient token (timedelta) |
| `src/core/metrics.py` | `platform_founder_jwt_reject_total`; **`tenant_jwt_claim_reject_total`** + `record_tenant_jwt_claim_reject()` (симметрия негативов iss/aud для tenant JWT) |

## Матрица verify (негативы)

| Токен | Условие | Ожидание |
|-------|---------|----------|
| Tenant admin | Подпись OK, неверный `aud` при strict legacy off | `JwtClaimValidationError` → **401**, `invalid_token_audience` |
| Tenant admin | Подпись OK, неверный `iss` | `invalid_token_issuer` |
| Founder access | Подпись founder key OK, неверный `aud` | `invalid_token_audience`; на `/platform/internal/*` — **401** + метрика `reason=audience` |
| Legacy | Оба `iss` и `aud` отсутствуют, `JWT_LEGACY_ALLOW_MISSING_ISS_AUD=true` | Допускается (dual-read) |
| Legacy | Только `iss` или только `aud` | `invalid_token_claims` |

## Тесты (без PII)

- **Файл:** `tests/unit/test_security_jwt_realm_e6.py`  
- **Запуск:** `TESTING=1 poetry run pytest tests/unit/test_security_jwt_realm_e6.py -v`  
- **Интеграция (strict `aud`):** `test_platform_internal_rejects_founder_jwt_wrong_audience_when_strict`, `test_admin_session_rejects_jwt_wrong_audience_when_strict`, `test_patient_booking_rejects_jwt_wrong_audience_when_strict` (при `JWT_LEGACY_ALLOW_MISSING_ISS_AUD=false`).

Интеграционные тесты с БД: см. зафиксированный прогон [QA_ARCH_PLATFORM_1A_API_DB_REGRESSION_2026-04-06.md](./QA_ARCH_PLATFORM_1A_API_DB_REGRESSION_2026-04-06.md) — **38 passed** (`test_platform_internal` + `test_platform_founder_totp` + `test_platform_billing`). Ожидания обновлены под 1a-E6 (401 на tenant JWT у контура Основателя) и единый envelope ошибок (`code` в корне тела ответа).

## Rollout

1. Выкатить код с `JWT_LEGACY_ALLOW_MISSING_ISS_AUD=true` (default).  
2. Убедиться, что все клиенты получают токены через API (login), а не старые ручные mint без claims.  
3. Выставить `JWT_LEGACY_ALLOW_MISSING_ISS_AUD=false` в production.

## Версия

2026-04-06
