# Расписание backup БД (SME §1.1)

> **Владелец:** @LEAD / операции. Репозиторий задаёт **скрипт и пример cron**; конкретное окно и retention — в политике деплоя.

## Скрипт

`scripts/ops/backup_postgres.sh` — логический дамп `pg_dump -Fc` в каталог (по умолчанию `./backups` или `BACKUP_DIR`).

Пример:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dental_booking"
export BACKUP_DIR="/secure/backups"
bash scripts/ops/backup_postgres.sh
```

Проверка: размер файла > 0; при необходимости `pg_restore -l` на копии.

## Пример cron (Linux, ежедневно 03:15 UTC)

```cron
15 3 * * * cd /opt/dental_booking && DATABASE_URL="..." BACKUP_DIR=/var/backups/dental ./scripts/ops/backup_postgres.sh >> /var/log/dental_backup.log 2>&1
```

## Retention

Минимум **7** полных дампов (SME); фактический срок — по регламенту @LEAD (ротация старых файлов вне репозитория).

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | Скрипт и пример cron (P0 QA closure) |
