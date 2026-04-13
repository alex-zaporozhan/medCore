# QA_ARCH: срез 1a-E5 — RLS на organization_entitlements

**Дата:** 2026-04-06  
**Epic:** 1a-E5  
**Статус:** закрыт по минимальному DoD (политика плюс тест при включённом GUC)

## Реализация

- Миграция `20260423_phase1a_founder_totp_org_ent_rls`: RLS FORCE на таблице `organization_entitlements`, политика `organization_entitlements_tenant_scope`.
- Режим по умолчанию: приложение не выставляет `app.rls_org_entitlements`, политика пропускает строки (основной путь — слой приложения, ADR-007 Option B).
- Режим проверки: `SET LOCAL app.rls_org_entitlements = 'on'` и `SET LOCAL app.effective_organization_id` — фильтр по организации.
- Amendment в [ADR-007](../adr/ADR-007-platform-multitenancy-super-admin.md).
- Тест: `tests/api/test_organization_entitlements_rls.py`.

## DoD

- [x] Политика в БД и описание bypass или enforce.
- [x] Amendment ADR-007.
- [x] Негатив или фильтрация в pytest при включённом режиме.

## Долг

- RLS на прочих tenant-таблицах — отдельный Enterprise-эпик.
