# LOY_FAMILY — LoyaltyGroup и `family_links.group_id` (Wave 3, I4)

## Назначение

После миграции `r4s5t6u7v8w9` доступны:

- таблица `loyalty_groups` — опциональная группировка семейных связей по клинике;
- nullable `family_links.group_id` → `loyalty_groups.id` (ON DELETE SET NULL).

Правила списания по-прежнему опираются на поля `FamilyLink` (лимиты, `can_spend_from_owner_loyalty`); группа — **метка/фильтр** для отчётов и UX, не замена проверок доступа.

## Данные до релиза

- Существующие строки `family_links` имеют `group_id = NULL`.
- Таблица `package_family_links` и логика пакетного шэринга не удаляются; два механизма могут сосуществовать (см. `ARCH_DEV_LOY_FAMILY_013_TASKS`).

## OPS

1. Применить миграции: `alembic upgrade head`.
2. При необходимости завести группы через SQL/будущий API и проставить `group_id` выборочно (без массового blind update в проде без бэкапа).
3. Откат: `alembic downgrade -1` снимает колонку и таблицу (см. `downgrade` миграции).

## Связанные ID бэклога

- **I2** — сущность `LoyaltyGroup`;
- **I3** — опциональный `group_id` на `family_links`;
- **I4** — этот runbook.
