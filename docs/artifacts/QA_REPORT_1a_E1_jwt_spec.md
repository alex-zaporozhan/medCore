# QA_ARCH: срез 1a-E1 — границы JWT / platform vs admin

**Дата:** 2026-04-06  
**Epic:** 1a-E1  
**Статус:** закрыт (спека + согласование с реализацией 1a-E2)

## Объём проверки

- Черновики: [PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](../architecture/specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md), [OWNER_API_SEMANTICS_U005_DRAFT.md](../architecture/specs/OWNER_API_SEMANTICS_U005_DRAFT.md).
- Решение LEAD: [SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md](../architecture/SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md).

## Выводы

1. **Realm:** JWT тенанта (`/admin/*`, patient) и JWT Основателя (`type=platform_founder`, `/platform/internal/*`, `/platform/auth/login`) описаны как раздельные; админский Bearer на platform-internal даёт **403** (или **401** при изолированном `PLATFORM_FOUNDER_JWT_SECRET`).
2. **`sub`:** для Основателя зафиксировано соответствие строке **`platform_founder_users.id`**; валидная подпись без строки в БД → **403** (`platform_founder_inactive_or_unknown`).
3. **`/owner/*`:** без U-005 не расширяется; черновик owner-семантики остаётся опорой для будущих маршрутов.
4. **Противоречия с кодом до среза:** ранее тесты минтили founder-JWT с произвольным `uuid4()`; после 1a-E2 это устранено через seed `PlatformFounderUser` в `tests/conftest.py`.

## Риски (остаточные)

- **1a-E3:** без 2FA учётная запись Основателя остаётся однофакторной — приёмлемо как промежуточный этап по roadmap.
- Операционный ручной mint JWT без строки в БД не запрещён на уровне кода (только политика); штатный путь — логин или выдача через API после записи в `platform_founder_users`.

## Рекомендации

- Следующий срез по плану: **1a-E3** (2FA), затем **1a-E4** / **1a-E5** по [STREAM_1A_PLATFORM_EPICS.md](../architecture/arch_plan/STREAM_1A_PLATFORM_EPICS.md).
