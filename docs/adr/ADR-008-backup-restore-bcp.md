# ADR-008: Backup, restore, непрерывность (BCP)

- **Статус:** Accepted (partial) — кластерный backup остаётся на managed-DB/OPS; в приложении: метрики логического экспорта `backup_logical_export_*` (Celery), алерт `BackupLogicalExportSuccessStale` (заглушить если экспорт не используется), runbook [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) §8.
- **Дата:** 2026-04-03  
- **Контекст:** В репозитории нет зафиксированной enterprise-политики backup/PITR, retention, шифрования и учений restore; локально Postgres в Docker volume ([docker-compose.yml](../../docker-compose.yml)). Ось BCP в [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](../architecture/LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) — 0.

## Решение (целевое)

### Прод (рекомендуемый контур)

- **Управляемый PostgreSQL** (RDS, Cloud SQL, Aiven и т.д.): автоматические снапшоты, **PITR** где доступно, retention по политике компании.
- Дополнительно: **логический экспорт** (pg_dump или pgBackRest logical) в **зашифрованное** object storage с отдельными ключами KMS; частота и retention — в runbook.
- **Restore drill** минимум quarterly на staging; метрики: `restore_success_rate`, длительность (см. [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) §6.1, [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) **2-F2**).

### Docker / on-prem без managed DB

- Документированный runbook: snapshot volume или `pg_basebackup` + периодический `pg_dump`; проверка восстановления на отдельном хосте.
- Явно зафиксировать **RPO/RTO** как цели, не как обещание без измерений.

### Tenant-scoped export

- Не путать полный backup кластера с **экспортом данных одной организации** (продуктовая фича под GDPR/договор); реализуется логическим выбором строк по `organization_id`/`clinic_id` в зашифрованный архив (см. ADR-007).

## Последствия

- OPS-владелец, секреты для backup storage, мониторинг просроченных бэкапов.

## Связь

- [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), [../architecture/09_backup_restore_bcp.md](../architecture/09_backup_restore_bcp.md).

## Outstanding (partial acceptance)

До снятия *partial* — **2-F2**, **2-F4**, **2-F6** в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) и указатель в [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md).
