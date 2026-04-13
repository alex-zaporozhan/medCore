# Фаза 1a — ядро платформы и изоляция (Phase_1a_Platform_Core)

**Узлы МП mermaid:** `Founder_auth_2FA_spec`, `Platform_DB_RLS`, `Signup_intent_pending_DB`.  
**Связь МП:** §1, §6 (хранение pending в БД), §9, §16.1, §17.1, §19 п.1–3, 10–12.

## Архитектурный целевой образ

1. **Отдельный контур доверия для Основателя** — issuer, claims, сроки; не смешивать с JWT админа клиники (МП §19 п.3).
2. **Platform-данные** — пользователь/сессии Основателя, audit platform-уровня (по ADR-007); **запрет** смешивать ORM-модели platform и tenant без барьера (МП §1).
3. **Изоляция tenant** — RLS fork **или** централизованные проверки + негативные тесты на критичные пути (МП §1, ADR-007).
4. **Pending подписка** — строки в БД платформенного контура (`signup_intent` / аналог), UTC, TTL, идемпотентность; Redis не единственный SoT (МП §6).
5. **Секреты prod** — схема не «только `.env`» для Основателя (МП §9, §19 п.12).
6. **2FA** — спека обязательности TOTP для Основателя после bootstrap-периода; для Владельца — до платного лендинга на чувствительных действиях (МП §9, §19 п.10).

## Порядок работ @DEV (рекомендуемый)

1. **Спеки OpenAPI / внутренние** для `/platform/...` vs `/admin/...` (черновик, согласованный с [backend/api_layer.md](../backend/api_layer.md)).
2. **Миграции** platform-сущностей и таблиц intent (если ещё не покрыто MVP spine — расширить, не дублируя контур B без идемпотентности).
3. **Middleware / dependencies** — извлечение platform-principal отдельно от `get_current_admin`.
4. **Тесты** — негативные cross-tenant сценарии (DoD **§15b 1a**).
5. **Документация OPS** — куда класть секреты, как ротировать (ссылка в runbook).

## Зависимости и блокеры

- **§17.1** должен быть записан **до** включения нескольких реплик на публичном контуре B/signup.
- **U-005** — не расширять `/owner/*` без отдельного решения.

## DoD (архитектурный минимум)

- Негативные тесты cross-tenant **N≥1** на домен (МП §15b 1a).
- Спека JWT: Основатель vs тенант.
- В репозитории нет «тихого» чтения platform-таблиц из хендлеров админки клиники.

## Ссылки

- [ADR-007](../../adr/ADR-007-platform-multitenancy-super-admin.md)
- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md)
- [specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](../specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md)

## Статус @DEV (фиксация прогресса)

- **2026-04-05:** зависимость `get_current_platform_founder`, маршрут `GET …/platform/internal/health`, тесты отказа для admin/patient JWT; секрет `PLATFORM_FOUNDER_JWT_SECRET` (опционально, иначе dev-режим на общем JWT-ключе — см. спеку).
- **2026-04-05:** негативный тест границы JWT: `platform_founder` на `GET /admin/auth/session` → **401**; артефакт grep-аудита A/B — [WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](../../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md).
- **2026-04-06 (1a-E6):** выдача и verify с `iss`/`aud` для admin, patient, `platform_founder` и MFA; dual-read `JWT_LEGACY_ALLOW_MISSING_ISS_AUD`; отчёт [QA_REPORT_1a_E6_jwt_hardening](../../artifacts/QA_REPORT_1a_E6_jwt_hardening.md).

## Полное закрытие фазы (сверх DoD)

Минимальный DoD §02 выполнен (см. [STREAM_1A_PLATFORM_EPICS.md](./STREAM_1A_PLATFORM_EPICS.md)). Строки **1a-F1…F5** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — **done**; поток **1a** закрыт @QA_ARCH: [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md), [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md). Остаточный долг (recovery codes, расширение RLS, immutable audit, FE-сессия и т.д.) — в [STREAM_1A_PLATFORM_EPICS.md](./STREAM_1A_PLATFORM_EPICS.md) и backlog, **не** отменяет закрытие стрима. Смежный пункт по цепочке admin JWT + entitlement (после профилирования лишнего hit БД): [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) B1, **1c-Q1**.