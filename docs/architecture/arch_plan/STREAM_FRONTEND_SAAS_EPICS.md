# Поток Frontend — SaaS (лендинг, Основатель, админка под гейты)

> **МП:** §5–§8, §12–§13 (меню по entitlement).  
> **Фронт-доки:** [frontend/routing_and_shells.md](../frontend/routing_and_shells.md), [frontend/api_state.md](../frontend/api_state.md).  
> **Индекс:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).  
> **PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-H1**, **PRC-H2**.

## QA_ARCH: префлайт для @ARCH и приёмка

**Цикл:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md). Инспектор: [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **Сквозное:** [STREAM_CROSS_CUTTING_GO_LIVE.md](./STREAM_CROSS_CUTTING_GO_LIVE.md), [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md).

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до @DEV** | Таблица **маршрут SPA → метод API → роль/публичность** для среза; для ошибок — маппинг на стабильные `code` ([PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md)); для **FE-E2** — диаграмма или список шагов **login → mfa_required → login/mfa** с полями ответа. Для публичного контура — где **rate limit / captcha** (даже если реализация в backend). |
| **Минимум в `QA_REPORT`** | Один **e2e smoke** (Playwright или согласованный) на путь среза **или** чеклист ручной приёмки с скриншотом/логом сети; проверка, что UI **не** показывает stack trace в prod-сборке; для гейтов меню — сверка с [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md) (строки в scope). |
| **Красные флаги** | «Страница есть» без вызова API; CTA ведёт на несогласованный контракт; MFA только в тексте без соответствия **1a-E3**; игнор **1b-F3** (privacy/антиспам) при заявлении готовности маркетингового контура. |

## Срезы

**FE-E1** — Маркетинговая оболочка: главная, тарифы, регистрация, согласие PII. DoD: маршруты SPA, вызовы публичных API; контракт с backend по C3 (rate limit, captcha). **Факт (2026-04):** на лендинге (`/`) есть блок тарифов с API каталога и CTA checkout (`POST /api/v1/public/platform/signup/checkout`) — см. **1b-E1** / [QA_REPORT_1b_E1_checkout.md](../../artifacts/QA_REPORT_1b_E1_checkout.md). Полный продуктовый контур (**1b-F3**: privacy, антиспам, отдельные страницы signup) остаётся открытым.

**FE-E2** — Кабинет Основателя: дашборды §7.1, список владельцев §7.2. DoD: зона роутинга; JWT platform после **1a-E2**; **UX под MFA** после **1a-E3** (шаг TOTP при логине, enroll только если продуктовый поток выносит в UI — до решения LEAD достаточно документированного контракта с API `login` / `login/mfa` / `totp/*`).

**FE-E3** — Админка клиники: меню по entitlement; экраны под platform и billing API. DoD: синхронизация с [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md); TanStack Query и guards.

## Зависимости

- **FE-E2** зависит от **1a-E2**; для корректного опыта входа Основателя учитывать **1a-E3** (TOTP / `mfa_token`).
- **FE-E1** параллелен **1b-E1** при зафиксированном публичном API; оставшийся долг маркетинга — **1b-F3** и [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md).

## Follow-up (после минимального лендинга + checkout)

- Turnstile / captcha на публичном checkout и лимиты — выравнивание с C3 и **1b-F3**.
- Отдельный маршрут **/pricing** (или эквивалент) вместо только секции на главной — согласование с Product/дизайн.

## QA_ARCH — приёмка и бэклог (2026-04-07)

**Отчёт (FE-срез 2026-04-07):** зафиксировано в [STREAM_FRONTEND_SAAS_EPICS.md](./STREAM_FRONTEND_SAAS_EPICS.md) (этот файл): усилены парсинг ошибок (единый envelope), `X-Request-Id` на публичном каталоге/checkout, явные состояния загрузки/ошибки каталога, исправлено чтение тела ответа при ошибке входа Основателя, добавлены vitest + e2e на редирект `/platform/*` без JWT. **Следующие этапы** (матрица маршрут→API, E2E с API, TOTP enroll в UI, персистенция consent, §7.2 owners API) — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md), блоки **FE-*** / **1b-F3**.

**Backend (справочно):** `POST /api/v1/platform/auth/login`, при включённом 2FA — ответ с `mfa_required` + `POST .../login/mfa`; bootstrap TOTP — `.../totp/enroll`, `.../totp/confirm`. Разбор **1a-E2:** [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md); **1a-E3:** [QA_REPORT_1a_E3_founder_2fa.md](../../artifacts/QA_REPORT_1a_E3_founder_2fa.md).

---

**Версия:** 2026-04-07 (QA_ARCH отчёт и бэклог — см. § выше).
