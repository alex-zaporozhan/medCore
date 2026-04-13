# QA_ARCH — демо-слой multi-tenant showcase (без Alembic)

**Цель:** воспроизводимая «живая» витрина продукта после `alembic upgrade head` + сиды.

## Команды (полная цепочка)

1. PostgreSQL доступен; `DATABASE_URL` указывает на созданную БД (см. `.env.example`).
2. `poetry install`
3. Схема: `poetry run alembic -c alembic.ini upgrade head`
4. RBAC: `poetry run python -m src.scripts.seed_rbac_baseline`
5. Showcase: `poetry run python -m src.scripts.seed_multi_tenant_showcase`

Скрипты сидов используют ORM: в metadata должны быть зарегистрированы таблицы под FK — в `showcase_saas_extras` импортируются **`Payment`** (`bookings.payment_id`) и **`Product`** (`tasks.inventory_product_id`); иначе `NoReferencedTableError` при flush. Колонки `TIMESTAMP WITHOUT TIME ZONE` (staff calendar, чат, promo/story) заполняются naive UTC (`_utc_naive_wall`), иначе asyncpg ругается на naive vs aware.

Если маркер `platform_signup_intents.notes = seed:multi_tenant_showcase_v1` уже есть, а демо-слой неполный:

```bash
poetry run python -m src.scripts.backfill_showcase_saas_extras
```

Далее **перелогин** в `/admin/login`.

## Что создаётся (идемпотентно)

| Область | Маркер / проверка |
|--------|-------------------|
| Commerce | код точки `SHOWCASE_DEMO_MAIN` |
| Записи пациентов (расписание врачей) | `bookings.notes = showcase_calendar_v1` |
| Kanban | `tasks.title` LIKE `Демо Kanban:%` + поток `task_streams.slug = general` + доска `clinic_wide` |
| Календарь сотрудника | `staff_calendar_events.title` LIKE `Демо календарь:%` |
| Лента | посты с префиксом `Демо CRM:` |
| Чат | комната `GENERAL` |

Реализация: `src/scripts/showcase_saas_extras.py`.

## Только пересоздать bookings showcase

См. SQL в `documentation/DEMO_MULTI_TENANT_CREDENTIALS.md` (DELETE по `notes`).

## Учётные данные

`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`
