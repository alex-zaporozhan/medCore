# Поток 1a — Platform Core: эпик-срезы

> **Статус потока (@QA_ARCH):** **закрыт** (срезы **E1–E6**, **1a-F1…F5**). Сводка и замена удалённых scratch-отчётов: [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md) (приложение B).  
> **МП:** [02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md), **§16.1**, ADR-007.  
> **Долг полного закрытия:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — **1a-F1…F5** закрыты срезами **1a-E2…E6** (в т.ч. **1a-F4** JWT `iss`/`aud` — **1a-E6**).  
> **Индекс:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).  
> **PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-A1…A5** (строки блока A).  
> **Моделирование @ARCH (полный FE+BE, E1–E6):** [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md).

Выполнять **по одному срезу** за цикл playbook (LEAD → ARCH → DEV → QA_ARCH).

## QA_ARCH: префлайт для @ARCH и приёмка

**Цикл:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md) (шаг **1** до кода, шаг **3–5** после). Инспектор: [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **PRC:** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) блок **A**.

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до @DEV** | Границы реалмов (Основатель / админ тенанта / пациент): таблица **issuer · audience · срок · MFA-ветка**; список **префиксов маршрутов** (`/platform/*`, `/admin/*`, публичные) и точка входа **Depends**; для RLS — какие таблицы/политики в срезе и **один** эталонный негатив cross-tenant (сущность + ожидаемый HTTP/код). Для **1a-E6** — явная матрица **verify** (что отклоняется при неверном `iss`/`aud`) без «сделаем в коде». |
| **Минимум в `QA_REPORT` после @DEV** | Ссылка на тесты по имени/пути; выдержка лога/ответа **без PII** для audit (если срез E4); для E5/E6 — **не менее одного** негатива «чужой токен / чужой realm» на согласованном маршруте. |
| **Красные флаги** | «JWT разный по тексту МП» без таблицы claims; негатив только на «нет токена»; audit с телом запроса/PII; расширение `/platform/*` без строки в **PHASE_FULL_CLOSURE** и **PRC-A***. |

## Срезы

**1a-E1** — Спека JWT: Основатель vs тенант; границы `/platform/*` vs `/admin/*`. DoD: документ и согласование LEAD; не расширять `/owner/*` без U-005.

**1a-E2** — Platform user в БД, аутентификация, выдача access (не ручной mint). DoD: миграции, API, негативные тесты доступа к platform. **Усиления (2026-04-06):** `503` на `POST /platform/auth/login` при `APP_ENV=production` и пустом `PLATFORM_FOUNDER_JWT_SECRET`; сквозной тест login → Bearer → `GET /platform/internal/health`; per-IP rate limit через dependency `require_platform_founder_login_ip_rate_limit`; OpenAPI `responses` 401/429/503 на login — см. [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md).

**1a-E3** — 2FA TOTP для Основателя и политика bootstrap. DoD: интеграционные тесты; ссылка на [FOUNDER_ACCESS_BREAKGLASS.md](../../operations/FOUNDER_ACCESS_BREAKGLASS.md).

**1a-E4** — Audit на критичных `/platform/*`. DoD: structured log или таблица audit без лишней PII.

**1a-E5** — RLS fork или эквивалентная политика и негативные тесты cross-tenant. DoD: ADR-007 amendment при необходимости; минимум один домен с негативом.

**1a-E6** — Ужесточение JWT (**1a-F4**): `iss` / `aud` и/или отдельный issuer для реалмов (МП **§19** п.3); согласование с [ADR-007](../../adr/ADR-007-platform-multitenancy-super-admin.md). DoD: выдача и verify для admin / patient / `platform_founder` (и MFA JWT при необходимости); негативные тесты на неверные `iss`/`aud`; политика rollout / env-флаг при необходимости; `docs/artifacts/QA_REPORT_1a_E6_jwt_hardening.md`.

**Отчёты:** отдельный `docs/artifacts/QA_REPORT_1a_E*.md` на критичные срезы (**E2**, **E5**, **E6**); шаблон приёмки — раздел **QA_ARCH** выше.

## Улучшения и долг после E3–E5 (не отдельные срезы до решения LEAD)

- **TOTP:** офлайн recovery codes (см. [FOUNDER_ACCESS_BREAKGLASS.md](../../operations/FOUNDER_ACCESS_BREAKGLASS.md)); отдельная политика сложности пароля для `platform_founder_users` vs админ клиники.
- **Audit:** иммутабельный audit в БД для чувствительных сущностей (пересечение с **1b-F7** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md)).
- **RLS:** расширение политик на другие tenant-таблицы (не только `organization_entitlements`); опционально единый паттерн `SET LOCAL` GUC на соединении — только после арх-ревью производительности и совместимости с пулом.

## После 1a-E5 (QA_ARCH)

- **Закрытие всего потока 1a:** [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md), [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) (блок **A**; **PRC-A3** — вне 1a, OPS/SEC).
- Срезы **1a-E3…E5** закрыты: [QA_REPORT_1a_E3_founder_2fa](../../artifacts/QA_REPORT_1a_E3_founder_2fa.md), [QA_REPORT_1a_E4_platform_audit](../../artifacts/QA_REPORT_1a_E4_platform_audit.md), [QA_REPORT_1a_E5_rls](../../artifacts/QA_REPORT_1a_E5_rls.md).
- Ретроспектива **1a-E2:** [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md).
- **1a-E6** (JWT `iss`/`aud`, **1a-F4**): реализация в `src/core/security.py` + отчёт [QA_REPORT_1a_E6_jwt_hardening](../../artifacts/QA_REPORT_1a_E6_jwt_hardening.md). Параллельно допустимы OPS-срезы observability (**OBS-2** / **OBS-3**).

---

**Усиления 1a-E2 (код + тесты):** см. раздел «Код» в [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md); риски — в том же файле и в [QA_REPORT_1a_E2_platform_user.md](../../artifacts/QA_REPORT_1a_E2_platform_user.md).

**Версия:** 2026-04-06 (закрытие потока: ARCH_MODEL + PRC-A; scratch QA_ARCH artifacts удалены, см. IMPLEMENTATION_REPORT §приложение B).
