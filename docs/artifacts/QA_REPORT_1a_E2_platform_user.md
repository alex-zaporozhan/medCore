# QA_ARCH: срез 1a-E2 — platform user в БД, логин, JWT

**Дата:** 2026-04-06  
**Epic:** 1a-E2  
**Статус:** закрыт (код + тесты)

## Реализация (факты)

| Компонент | Путь / заметка |
|-----------|----------------|
| Модель | `src/domain/entities/platform_founder_user.py`, таблица `platform_founder_users` |
| Миграция | `alembic/versions/20260422_platform_founder_users.py` |
| Логин | `POST /api/v1/platform/auth/login` — `src/api/v1/routers/platform_founder_auth.py` |
| Зависимость | `get_current_platform_founder` в `src/api/v1/dependencies.py` (загрузка активного пользователя по `sub`) |
| TTL / лимиты | `src/core/config.py`: `jwt_access_token_expire_minutes_platform_founder`, `rate_platform_founder_login_*`, `rate_platform_founder_auth_*` |
| Bootstrap | `python -m src.scripts.create_platform_founder_user` |
| Тесты | `tests/conftest.py` (seed + `platform_founder_auth`), `tests/api/test_platform_internal.py`, правки platform billing / catalog |

## DoD

- [x] Миграция таблицы учётных записей Основателя.
- [x] Выдача JWT после проверки email/пароля; 503 при не настроенном founder JWT в prod-режиме (как у internal).
- [x] Негатив: админский / patient JWT на `/platform/internal/*` — отказ.
- [x] Негатив: founder JWT с неизвестным `sub` — **403** с кодом `platform_founder_inactive_or_unknown`.
- [x] Pytest: существующие сценарии platform internal / billing / catalog используют seeded `platform_founder_id`.

## Риски

- Пароли Основателя используют тот же пайплайн хеширования, что и админы (`admin_auth`); отдельная политика сложности пароля для platform не введена (вне среза).
- 2FA не входит в 1a-E2 (**1a-E3**).

## Пост-ревью (QA_ARCH)

- Полный разбор исполнения, риски и бэклог этапов: [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](./IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md).
- **1a-F1** в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) закрыт (**done**) в соответствии с этим срезом.
- Дополнительные тесты после ревью: `test_platform_founder_login_503_in_production_when_founder_secret_unset`, `test_platform_founder_login_token_valid_for_internal_health` в `tests/api/test_platform_internal.py`.
