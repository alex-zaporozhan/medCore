# Тестовая база для pytest (`dental_booking_test`)

## Симптом

При `poetry run pytest` ошибка:

```text
asyncpg.exceptions.InvalidCatalogNameError: database "dental_booking_test" does not exist
```

Это значит: Postgres доступен, но **базы с именем `dental_booking_test` ещё нет**. Отдельный файл `.env.test` в репозитории не используется — тесты читают **`DATABASE_URL_TEST`** из корневого `.env` (см. `tests/conftest.py`).

## Что нужно один раз

### 1. Переменные в `.env`

Скопируйте из `.env.example` и приведите к своему хосту/порту/паролю:

- `DATABASE_URL` — основная БД разработки (например `.../dental_booking`).
- **`DATABASE_URL_TEST`** — та же строка подключения, но **имя БД** `dental_booking_test` (порт и пароль как у `DATABASE_URL`).

**Порт хоста** должен совпадать с пробросом в `docker-compose.yml` (сервис `db`, сейчас **`5442:5432`** — с хоста `localhost:5442`). Если меняли порт в compose — обновите и `.env`.

```env
DATABASE_URL_TEST=postgresql+asyncpg://postgres:ВАШ_ПАРОЛЬ@localhost:5442/dental_booking_test
```

Если `DATABASE_URL_TEST` не задан, pytest подставит `dental_booking_test` в URL из `DATABASE_URL` автоматически — пароль и хост должны быть корректны в `DATABASE_URL`.

### 2. Создать пустую БД `dental_booking_test`

Postgres должен быть запущен (`docker compose up -d db redis` или локальный сервис).

**Вариант A — Docker (рекомендуется, `psql` не нужен на хосте):**

```powershell
docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"
```

Если контейнер называется иначе: `docker ps` → имя контейнера с `postgres`.

**Вариант B — `psql` на хосте** (если установлен и в PATH):

```powershell
psql -U postgres -h localhost -p 5442 -c "CREATE DATABASE dental_booking_test;"
```

Если БД уже существует, команда вернёт ошибку «already exists» — это нормально.

### 3. Накатить схему (Alembic head)

**Один источник правды:** схема тестовой БД = **`alembic upgrade head`** (как prod). При прогоне `pytest` фикстура `init_db` выполняет те же миграции автоматически.

Вручную из корня (если пароль в `.env` совпадает с Postgres и порт верный):

```powershell
poetry run python scripts/upgrade_test_db.py
```

Скрипт подставляет `DATABASE_URL_TEST` в `DATABASE_URL` и выполняет `alembic upgrade head`. Без созданной БД и миграций тесты могут падать с ошибками подключения или `UndefinedColumnError`.

**Вариант C — с хоста не удаётся (`password authentication failed`):** накатить миграции **из контейнера `backend`**, подставив ту же БД, что у API, но с именем `dental_booking_test` (учётные данные как у работающего backend):

```powershell
docker compose exec backend python -c "import os, subprocess; u=os.environ.get('DATABASE_URL',''); u=u.replace('/dental_booking','/dental_booking_test',1) if 'dental_booking_test' not in u else u; os.environ['DATABASE_URL']=u; subprocess.check_call(['alembic','upgrade','head'])"
```

После успешного прогона проверьте, что в `.env` для pytest указан **тот же пароль и порт**, что реально принимает Postgres с хоста (см. `POSTGRES_PASSWORD` и проброс порта).

### 4. Запуск тестов

```powershell
poetry run pytest tests/
```

---

## Частые проблемы

| Проблема | Что проверить |
|----------|----------------|
| `password authentication failed` | Пароль в `DATABASE_URL` / `DATABASE_URL_TEST` совпадает с `POSTGRES_PASSWORD` в `.env` и с тем, с которым поднят контейнер Postgres. Либо используйте вариант C выше для миграций, затем выровняйте `.env`. |
| Порт | С хоста смотрите **`docker compose ps`** и колонку PORTS у сервиса `db` (по умолчанию **5442**). |
| `Can't locate revision` при `docker compose run migrations` | Job `migrations` должен собираться из **локального** `Dockerfile` (в репозитории не закрепляем устаревший образ registry-only для этого сервиса). Выполните `docker compose build migrations` и снова `docker compose run --rm migrations`. |
| Тесты SKIP вместо ошибки | См. сообщение в `conftest` — возможно, подключение к БД отключено. |

Подробности про пароли и варианты URL — в шапке **`tests/conftest.py`**.
