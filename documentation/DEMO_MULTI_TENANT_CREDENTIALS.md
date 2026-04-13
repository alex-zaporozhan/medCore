# Демо: учётные записи multi-tenant showcase

> **Только для локального / закрытого стенда.** Пароли и почты `@showcase-mt.demo` не использовать в продакшене.

Порядок вместе с образами для VPS: **`documentation/VPS_IMAGE_AND_DATA.md`**.

После `alembic upgrade head` выполните:

```bash
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

Один пароль для всех перечисленных админских пользователей:

`ShowcaseMT2026!`

Роли в продукте: **владелец** — глобальная роль `owner`; **администраторы** — `admin`; **маркетологи** — глобальная роль `manager` (в матрице прав есть маркетинг и широкий операционный доступ).

Учётная запись **Основателя платформы** этим сидом не создаётся: `poetry run python -m src.scripts.create_platform_founder_user --email ... --password ...`.

## Владельцы (owner)

| Город / юрлицо | Email |
|----------------|-------|
| Казань, ООО «Улыбка Плюс» | owner.kazan@showcase-mt.demo |
| Нижний Новгород, «Дентал-Про НН» | owner.nizhny@showcase-mt.demo |
| Самара, «Семейная стоматология Самара» | owner.samara@showcase-mt.demo |
| Краснодар, «Имплант-Эксперт Юг» | owner.krasnodar@showcase-mt.demo |
| Ростов, «Премьер Дент Юг» | owner.rostov@showcase-mt.demo |

## Администраторы (admin)

| Email |
|-------|
| admin1.kazan@showcase-mt.demo |
| admin2.kazan@showcase-mt.demo |
| admin1.nizhny@showcase-mt.demo |
| admin2.nizhny@showcase-mt.demo |
| admin1.samara@showcase-mt.demo |
| admin2.samara@showcase-mt.demo |
| admin1.krasnodar@showcase-mt.demo |
| admin2.krasnodar@showcase-mt.demo |
| admin1.rostov@showcase-mt.demo |
| admin2.rostov@showcase-mt.demo |

## Маркетологи (manager)

| Email |
|-------|
| marketing1.kazan@showcase-mt.demo |
| marketing2.kazan@showcase-mt.demo |
| marketing1.nizhny@showcase-mt.demo |
| marketing2.nizhny@showcase-mt.demo |
| marketing1.samara@showcase-mt.demo |
| marketing2.samara@showcase-mt.demo |
| marketing1.krasnodar@showcase-mt.demo |
| marketing2.krasnodar@showcase-mt.demo |
| marketing1.rostov@showcase-mt.demo |
| marketing2.rostov@showcase-mt.demo |

## Пароль (все строки выше)

`ShowcaseMT2026!`

Повторная генерация таблицы из кода:

```bash
poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials
```
