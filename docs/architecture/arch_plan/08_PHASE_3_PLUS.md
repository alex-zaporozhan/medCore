# Фаза 3+ — vertical, импорт, enterprise (Phase_3_Plus)

**Узел МП mermaid:** `Vertical_import_enterprise`.  
**Связь МП:** §14, §25, §16.4, ADR-010, [modules/data_migration_import_connectors.md](../modules/data_migration_import_connectors.md), U-010.

## Архитектурный целевой образ

### Universal SaaS / vertical (§14)

1. `industry_profile` на `Organization` + i18n и feature flags; дефолт `industry_dental` до переключения.
2. Негативные тесты: generic-профиль не открывает стомато-специфику там, где политика «скрыть».
3. Не ломать публичные dental API без версии (МП §14 чеклист).

### Импорт и enterprise-мигратор (§25)

1. Конвейер: ingest → validate → clean → match/merge → staging → commit → export (МП §25.0).
2. **v1 без обязательного AI**; AI-assist только как entitlement и под Sanitizer/лимиты (МП §25.1).
3. **§25.3** до первого PR batch-commit: размер батча, batch-id, откат по чанкам, очередь для тяжёлых загрузок.
4. Entitlements: `import.crm_v1` vs `import.enterprise_migrator` (МП §4, §16.4) — не путать «купил коннектор» с «модуль включён».

## Порядок работ @DEV

1. Расширить ADR-010 и модуль коннекторов профилями источников; UI мастера импорта.
2. Staging-область per org; dry-run отчёт «что изменится».
3. Идемпотентный commit батчами; аудит «кто запустил».
4. Связать с offboarding/export (§1e) для выгрузок.

## DoD

- Импорт v1 не обходит RBAC/entitlement.
- Спека батчей §25.3 согласована и внедрена до «большого» импорта.

## Ссылки

- [05_data_migrations_multitenancy.md](../05_data_migrations_multitenancy.md)
- [ADR-010](../../adr/ADR-010-external-crm-import-scope.md)

## Статус @DEV (2026-04-06)

- **Vertical §14:** колонка `organizations.industry_profile` (`industry_dental` / `industry_generic`), поле в `GET /admin/auth/session`, чтение `GET /admin/organization/industry-profile`, смена **`PATCH …/industry-profile`** (роль **owner** + `manage_crm`).
- **Гейт медкарты:** при `organization_id` клиники и профиле ≠ dental — **403** `medical_module_industry_not_dental` на маршрутах `admin_patient_medical`.
- **Импорт v1 (каркас):** entitlement **`import.crm_v1`** (каталог + box-blocked), `POST/GET …/admin/organization/crm-import/*`, таблица staging, идемпотентность dry-run; спека §25.3 — [data_migration_import_connectors.md](../modules/data_migration_import_connectors.md).
- **Тесты:** `tests/api/test_phase3_vertical_import.py`; узкий CI — [build-and-test-entitlements.yml](../../../.github/workflows/build-and-test-entitlements.yml).

## Статус @QA_ARCH (2026-04-06)

- **Ревью:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (секция **Фаза 3+**).
- **Усиления в коде:** effective-org для гейта импорта (`get_crm_import_organization_id`), проверка расхождения admin/clinic org, allowlist `source_profile`, метрика `crm_import_operations_total`, доп. негативные тесты.
- **Долг сверх DoD:** таблица **3-F** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (полный конвейер §25, аудит vertical/import, выравнивание entitlement для прочих роутеров, публичный контракт §14, дашборды по метрике импорта, UI мастера).

## Следующие этапы (зафиксировано QA_ARCH)

- **Строки эпика и статусы:** **3-F1…3-F6** — только в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (секция «Фаза 3+»).
- **Связь с жизненным циклом арендателя:** экспорт / offboarding в продукте — [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md), бэклог **1e-F3**; в плане @DEV п.4 — связать импорт с выгрузками §1e.
- **Публичный контракт ошибок (витрины, интеграции):** **1c-Q2**, **1c-Q4** в том же бэклоге; пересечение с **3-F4** (§14, публичные dental API).
