# Data migration: external CRM/ERP import

**Status:** target architecture; connectors are separate epics.  
**ADR:** [ADR-010](../../adr/ADR-010-external-crm-import-scope.md).  
**UNRESOLVED:** U-010.

## Phase A foundation

- Canonical entities v1: contact/patient, lead/deal, service/price line.
- Mapping: external_system, external_id, internal UUID, organization_id, clinic_id.
- Idempotency key: (source, entity_type, external_id).
- Pipeline: validate, staging, batch merge; import error report.

## Phase B connectors

| Source | v1 interface | Notes |
|--------|--------------|-------|
| Bitrix24 | REST, CSV fallback | Contacts, deals |
| 1C | One agreed exchange format | Depends on customer config |
| Other | CSV column mapping | Fastest path |

## Out of v1

- Real-time two-way sync; PHI documents without separate ADR.

## Enterprise audit

- Critical: import without clinic_id scope risks tenant leak.
- Add cross-tenant negative tests and queue for large files.

## §25.3 Batch commit and idempotency (before first heavy import PR)

**Статус:** зафиксировано для @ARCH / @DEV (МП §25.3, PRINCIPLE цикл 2).

- **Максимальный размер батча** commit (строк или сущностей) — параметр конфигурации или константа в ADR-010 appendix; значение по умолчанию согласовать с envelope БД (§31).
- **Идемпотентный `batch_id`** / ключ загрузки: уникальность на уровне `(organization_id, idempotency_key)` или эквивалент; повтор POST не создаёт второй commit.
- **Таймаут HTTP / воркера:** при превышении — явное состояние job (`partial`, `retryable`), без «тихого» частичного применения без строки в БД.
- **Откат по чанкам:** транзакции по чанкам внутри одного job; при ошибке — отметка чанка и возможность resume (очередь).
- **Тяжёлые файлы:** очередь (Celery) + чанки, не один монолитный commit на весь файл.

**Факт кода (Phase 3+ старт):** таблица `crm_import_staging_jobs`, эндпоинт `POST /admin/organization/crm-import/dry-run` (заглушка), идемпотентность по `idempotency_key` per org — см. `admin_crm_import.py`.

### PRINCIPLE

[FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).
