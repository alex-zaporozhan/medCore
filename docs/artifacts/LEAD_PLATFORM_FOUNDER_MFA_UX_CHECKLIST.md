# PRC-H2 — UX MFA кабинета Основателя (чеклист LEAD + QA)

Маршруты: `PlatformFounderLoginPage`, `PlatformFounderLayout`, TOTP enroll в зоне `/platform/*` (см. фронт `frontend/src/marketing/pages/`).

## Сценарии приёмки

| # | Сценарий | Ожидание | Статус |
|---|----------|----------|--------|
| H2-1 | Логин email/password без TOTP при `PLATFORM_FOUNDER_TOTP_REQUIRED` в проде | После пароля — шаг MFA или явное сообщение о необходимости TOTP (см. бэкенд политику) | _QA_ |
| H2-2 | Успешный TOTP | Доступ к `/platform/internal/*` | _QA_ |
| H2-3 | Неверный TOTP | Ошибка без утечки лишней информации; rate limit на `/platform/auth/login/mfa` | _QA_ |
| H2-4 | Break-glass | [FOUNDER_ACCESS_BREAKGLASS.md](../operations/FOUNDER_ACCESS_BREAKGLASS.md) исполним OPS | _OPS_ |

**Подпись LEAD (периметр релиза):** _________________ **Дата:** _______

**Версия:** 2026-04-06
