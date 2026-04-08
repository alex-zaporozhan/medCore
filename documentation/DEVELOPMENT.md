# Разработка и окружение

## Стек

- Python 3.11+, Poetry, PostgreSQL, Redis  
- Frontend: Node.js 18+, npm  
- Docker Compose — для БД и Redis (см. корневой `README.md`)

## Порты (типично)

- API: **8000**  
- Vite dev: **5175** (или значение из вывода `npm run dev`)

Если список клиник в админке не грузится — проверьте, что бэкенд запущен на порту API. См. также корневой `README.md` и `docker-compose.yml`.

## Тестовая база

1. Создайте БД `dental_booking_test` (один раз), например через `docker exec` к контейнеру Postgres из `docker-compose.yml`.  
2. В `.env` задайте `DATABASE_URL_TEST` на эту БД (тот же пользователь/пароль, что и для основной `DATABASE_URL`, с заменой имени БД).  
3. Миграции: из корня репозитория `alembic upgrade head` с переменными окружения, указывающими на тестовую БД, либо `python scripts/upgrade_test_db.py` — как принято в вашей среде.

Если `alembic_version` рассинхронизирован со схемой, согласуйте с командой порядок `stamp` / `upgrade` (опасные операции на общих инструкциях не фиксируются здесь).

## Полезные пути в репозитории

- `tests/conftest.py` — фикстуры и подсказки по `DATABASE_URL_TEST`  
- `alembic/versions/` — миграции схемы  
- `alembic/versions/README.md` — про архив старых миграций в `versions_archive/`  
- `.env.example` — перечень переменных окружения

## RBAC: снимок прав в роутерах

Файл **`documentation/rbac_router_permissions.txt`** должен совпадать с вызовами `require_permissions` в `src/api/v1/routers/`.

- Проверка: из корня репозитория  
  `python scripts/audit_rbac_endpoints.py --check`  
- Обновление списка после изменения прав:  
  `python scripts/audit_rbac_endpoints.py --write`  
- В CI дублируется тест: `pytest tests/application/test_sec_rbac_router_permissions_inventory.py`

## Политика ссылок из кода

Прикладной код не должен указывать пути к закрытому дереву **`/docs`** или внутренним паспортам. Допустимые отсылки на текст в git — только под **`documentation/`** и корневые файлы вроде **`DOCUMENTATION_POLICY.md`** (см. там же).
