# Разработка и окружение

## Стек

- Python 3.11+, Poetry, PostgreSQL, Redis  
- Frontend: Node.js 18+, npm  
- Docker Compose — для БД и Redis (см. корневой `README.md`)

## Порты (типично)

- API (host uvicorn): **8000**  
- API (Docker Compose publish): **8010** → контейнер 8000  
- Vite dev: **5175** (прокси `/api` на живой API: 8000, иначе 8010)  
- Vite preview: **4173** (тот же прокси)  
- Compose SPA: **3010**

Если список клиник в админке не грузится — проверьте, что бэкенд запущен на порту API. См. также корневой `README.md` и `docker-compose.yml`.

## Тестовая база

1. Создайте БД `dental_booking_test` (один раз), например через `docker exec` к контейнеру Postgres из `docker-compose.yml`.  
2. В `.env` задайте `DATABASE_URL_TEST` на эту БД (тот же пользователь/пароль, что и для основной `DATABASE_URL`, с заменой имени БД).  
3. Миграции: из корня репозитория `poetry run alembic upgrade head` (или `alembic upgrade head` из активированного venv) с переменными окружения, указывающими на целевую БД; локально для тестовой БД допустим `python scripts/upgrade_test_db.py`. После выката релиза с изменениями схемы ту же команду нужно выполнить **на каждой среде с БД** (staging, production и т.д.).

Если `alembic_version` рассинхронизирован со схемой, согласуйте с командой порядок `stamp` / `upgrade` (опасные операции на общих инструкциях не фиксируются здесь).

## pytest: долгий прогон и «зависания» (QA_ARCH)

- **Таймаут на тест:** в `pyproject.toml` включён `pytest-timeout` (по умолчанию **180 с** на тело теста, без учёта session-фикстур). Зависший тест падает с `Failed: Timeout (>180s)` вместо бесконечного ожидания. Для редкого долгого сценария: `@pytest.mark.timeout(600)` на тесте или модуле.
- **Postgres `too many clients`:** на одном инстансе Postgres не держите параллельно тяжёлые потребители соединений и полный `pytest tests/` (например **остановите** `docker compose` сервисы `backend`, `celery`, `celery-beat`, если они смотрят в тот же сервер). Иначе лимит `max_connections` исчерпывается суммарно по всем БД инстанса.
- **`httpx` + `ASGITransport` + бесконечный streaming:** транспорт ждёт завершения всего ASGI-ответа; `AsyncClient.stream()` к SSE «навсегда» не подходит. Для таких случаев в тестах вызывайте приложение напрямую (см. `tests/api/test_admin_omni_chat.py`, хелпер `_first_asgi_sse_body_chunk`) или ограничивайте жизнь стрима и закрывайте клиент.
- **Диагностика медленных тестов:** `poetry run pytest tests/ --durations=25 -q` (после успешного прогона покажет 25 самых долгих).
- **Индикатор «%» в IDE (Cursor/VS Code) долго не двигается:** процент обычно считается по **завершённым** тестам. Пока не закончится **session-фикстура** (`init_db`: `alembic upgrade head`; затем `truncate_tables` + `seed_data`) или один **очень долгий** тест, счётчик может стоять на месте **много минут** — это не обязательно зависание всего набора. Первый тяжёлый прогон миграций на пустой БД особенно долог. Для «что сейчас делает pytest»: запуск из терминала с `-v` / `--setup-show` или отключение тихого режима (`-q` убрать).
- **Слот врача в pytest:** `seed_data` живёт на всю сессию, `bookings` между тестами не чистятся. Новые записи в статусах, которые **занимают** слот (`pending` / `confirmed` / `awaiting_payment` и т.д.), берите через `tests.booking_slot.unique_booking_slot` (или `unique_clock_time`, если день обязан остаться «сегодня»). `datetime.now().time()` и фиксированные `time(17, 57)` на `seed_data["date"]` дают `UniqueViolationError` на `ux_bookings_doctor_slot_active` и валят локальный pre-push. Отмена / `no_show` / `completed` слот **не** занимают (partial unique index).

## Полезные пути в репозитории

- `tests/conftest.py` — фикстуры и подсказки по `DATABASE_URL_TEST`  
- `alembic/versions/` — миграции схемы  
- `alembic/versions/README.md` — про архив старых миграций в `versions_archive/`  
- `.env.example` — перечень переменных окружения  
- Паспорта экранов SPA (только `docs/`, не рантайм): `scripts/gen_frontend_page_passport_stubs.py` — `verify` / `generate`; маркеры **«не заполнено»** в `.md` — черновики документации, не путать с отложенными задачами в прикладном коде.

## RBAC: снимок прав в роутерах

Файл **`documentation/rbac_router_permissions.txt`** должен совпадать с вызовами `require_permissions` в `src/api/v1/routers/`.

- Проверка: из корня репозитория  
  `python scripts/audit_rbac_endpoints.py --check`  
- Обновление списка после изменения прав:  
  `python scripts/audit_rbac_endpoints.py --write`  
- В CI дублируется тест: `pytest tests/application/test_sec_rbac_router_permissions_inventory.py`

## Политика ссылок из кода

Прикладной код не должен указывать пути к закрытому дереву **`/docs`** или внутренним паспортам. Допустимые отсылки на текст в git — только под **`documentation/`** и корневые файлы вроде **`DOCUMENTATION_POLICY.md`** (см. там же).
