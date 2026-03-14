# Миграции Alembic

Старые 43 миграции перенесены в `alembic/versions_archive/` (очистка «кэша», см. docs/ARCH_ALEMBIC_MIGRATIONS.md).

В эту папку кладётся **одна** начальная миграция с полной схемой (revision id, например, `schema_v2_initial`), сгенерированная через:

```bash
alembic revision --autogenerate -m "schema_v2_initial"
```

при пустой БД. Дальнейшие миграции добавляются сюда же с коротким `down_revision`.
