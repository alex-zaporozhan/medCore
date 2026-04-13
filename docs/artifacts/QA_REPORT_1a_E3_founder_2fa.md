# QA_ARCH: срез 1a-E3 — TOTP для Основателя платформы

**Дата:** 2026-04-06  
**Epic:** 1a-E3  
**Статус:** закрыт по минимальному DoD (код + интеграционные тесты)

## Реализация

| Компонент | Путь / заметка |
|-----------|----------------|
| Модель | `platform_founder_users.totp_secret_ciphertext`, `totp_enabled` |
| Миграция | `alembic/versions/20260423_phase1a_founder_totp_org_ent_rls.py` (часть колонок TOTP) |
| Шифрование секрета | `src/infrastructure/crypto/platform_founder_totp_crypto.py` (Fernet от `SECRET_KEY`) |
| MFA JWT | `create_platform_founder_mfa_token` / `parse_platform_founder_mfa_token` в `src/core/security.py` |
| API | `POST /api/v1/platform/auth/login` (опционально `totp_code`), `POST .../login/mfa`, `POST .../totp/enroll`, `POST .../totp/confirm` |
| Bootstrap | Пока `totp_enabled=false`: вход по паролю; затем enroll → confirm с Bearer |
| Break-glass | Обновлён [FOUNDER_ACCESS_BREAKGLASS.md](../operations/FOUNDER_ACCESS_BREAKGLASS.md) |
| Тесты | `tests/api/test_platform_founder_totp.py` |

## DoD

- [x] TOTP (pyotp), enroll/confirm, двухшаговый логин при включённом 2FA.
- [x] Интеграционные тесты (pytest).
- [x] Ссылка на break-glass в операционном документе.

## Остаточные риски

- Офлайн recovery codes не реализованы (см. break-glass: сброс через OPS/БД).
- Отдельная политика сложности пароля для platform вне среза.
