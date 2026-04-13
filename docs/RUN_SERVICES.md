# Запуск и перезапуск сервисов Dental Booking

Краткая инструкция по порядку запуска и перезапуска всех билдеров и сервисов.

---

## Когда что удалять (перед командами)

- **Полный сброс БД (чистый старт):** остановите контейнеры (`docker-compose down`), удалите каталог `pgdata` (или том с данными Postgres). Затем `docker-compose up -d postgres redis`, дождитесь готовности Postgres, выполните миграции (см. раздел «Миграции»), затем поднимите остальные сервисы. Файлы в `alembic/versions/` **не удаляйте** — по ним накатываются миграции.
- **500 в чате (таблицы чата не найдены) или 500 на /clinics (column theme_primary_color does not exist):** убедитесь, что миграции применены **при запущенном Postgres** (см. раздел «Миграции»). Удалять `pgdata` не обязательно — достаточно `poetry run alembic upgrade head` (или `docker compose exec api alembic upgrade head` при API в Docker).
- **Только перезапуск сервисов:** ничего удалять не нужно; достаточно команд из раздела «Порядок запуска» / «Перезапуск».
- **Меняли миграции в коде:** если уже накатывали их на БД — лучше откатить до нужной ревизии (`alembic downgrade <revision>`) или сбросить БД (см. выше). Удалять файлы из `versions/` не обязательно и не рекомендуется, если миграции уже применялись.

---

## Требования

- **Backend:** Python 3.11+, Poetry, PostgreSQL, Redis
- **Frontend:** Node.js 18+, npm
- **Опционально:** Docker и Docker Compose (для БД и Redis)
- **Время:** метки и границы периодов — `docs/METRICS_PROTOCOL.md` (таймзона в карточках метрик), общий NFR-контекст — `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md`.

---

## 1. Первый запуск (один раз)

### Backend

```powershell
# В корне проекта d:\CURSOR\projects\dental_booking
poetry install
copy .env.example .env
# Заполните .env: DATABASE_URL, REDIS_URL и при необходимости прочие переменные
```

### База данных и Redis

**Вариант A — через Docker:**

В этом проекте Postgres и Redis в Docker проброшены на **5442** и **6380** (см. `docker-compose.yml`, чтобы не конфликтовать с локальными 5432/6379). В `.env` для запуска с хоста (uvicorn, alembic, pytest) укажите:
- `DATABASE_URL=...@localhost:5442/dental_booking`
- `REDIS_URL=redis://localhost:6380/0` (и при необходимости `REDIS_URL_TEST=redis://localhost:6380/0`, `DATABASE_URL_TEST=...@localhost:5442/dental_booking_test`).

```powershell
docker-compose up -d postgres redis
```

**Вариант B:** установите PostgreSQL и Redis локально и укажите их в `.env`.

**Если контейнеры postgres/redis в состоянии «Waiting» и не стартуют:**

1. **Порты 5432 или 6379 заняты** — другой процесс (локальный Postgres/Redis, другой контейнер) держит порт. Проверка (PowerShell):
   ```powershell
   Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
   Get-NetTCPConnection -LocalPort 6379 -ErrorAction SilentlyContinue
   ```
   Если порт занят: остановите процесс или смените порты в `docker-compose.yml` (например `"5442:5432"` для postgres) и в `.env` (если подключаетесь с хоста — `localhost:5442`).

2. **Запустите только инфраструктуру и посмотрите логи:**
   ```powershell
   docker compose down
   docker compose up -d postgres redis
   docker compose ps
   docker compose logs postgres redis
   ```
   Если в логах ошибка бинда порта (e.g. "address already in use") — освободите порт. Если ошибка тома/диска — проверьте путь `./pgdata/postgres` (права, антивирус).

3. **После смены портов или очистки** снова: `docker compose up -d postgres redis`, затем миграции и остальные сервисы.

### Миграции

**Обязательно** выполните после клона/обновления кода, иначе возможны 500 при открытии страниц (API обращается к таблицам, которых ещё нет).

Деплой на VPS (Docker Hub, пустая схема vs сиды для Основателя и клиник): см. **`documentation/VPS_IMAGE_AND_DATA.md`** и **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**.

**Важно:** миграции нужно применять **к той же БД, к которой подключается API**, и **когда Postgres уже запущен**.

- **API запускаете на хосте (uvicorn):** поднимите Postgres и Redis, затем в корне проекта:
  ```powershell
  docker-compose up -d postgres redis
  poetry run alembic upgrade head
  ```
- **API запускаете в Docker (docker-compose up api):** поднимите Postgres и Redis, затем примените миграции **в том же окружении** (тот же хост БД), чтобы таблицы создались в контейнере Postgres:
  ```powershell
  docker-compose up -d postgres redis
  # Вариант 1: с хоста (подключение к localhost:5432 — тот же Postgres)
  poetry run alembic upgrade head
  # Вариант 2: из контейнера API (подключение к postgres:5432 — тот же Postgres)
  docker-compose run --rm api alembic upgrade head
  ```
  После этого: `docker-compose up -d --build` (или `docker-compose up -d api`).

**Неверный порядок (миграции не применятся):** выключить весь Docker, выполнить только `poetry run alembic upgrade head` (Postgres не запущен — ошибка подключения), затем `docker-compose up -d`. Таблицы в БД не появятся.

### Тестовая БД для pytest

Полная пошаговая инструкция (ошибка `database "dental_booking_test" does not exist`, `DATABASE_URL_TEST`, миграции на тестовую БД): **[documentation/DEVELOPMENT.md](../documentation/DEVELOPMENT.md)**.

Кратко:

1. В `.env` задайте `DATABASE_URL_TEST` (см. `.env.example`) — отдельный файл `.env.test` не используется.
2. Создайте пустую БД (если `psql` не в PATH — через Docker):

   ```powershell
   docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"
   ```

   Если БД уже есть, Postgres вернёт «already exists» — это нормально.

3. Накатите схему на тестовую БД: `poetry run python scripts/upgrade_test_db.py`
4. Запуск: `poetry run pytest tests/ -v`

### Демо-данные (опционально)

Чтобы заполнить БД первой клиники 4 врачами, 10 пациентами и 10 услугами (или дополнить уже созданную клинику):

```powershell
poetry run python -m src.scripts.seed_demo_data
```

Скрипт создаёт клинику, если её ещё нет, и добавляет врачей с расписанием Пн–Пт 09:00–18:00, пациентов с телефонами +70000000001 … +70000000010 и стоматологические услуги. Также заполняет связи «врач–услуга» (service_doctors), чтобы при записи не возникала ошибка «This doctor does not provide this service».

Чтобы наглядно заполнить расписание записями (всем врачам, с пустыми окошками):

```powershell
poetry run python -m src.scripts.seed_demo_bookings
```

Добавляет записи на вчера, сегодня и следующие 4 дня; ~55% слотов занято, остальные остаются свободными.

### Frontend

```powershell
cd frontend
npm install
```

**Тарифы отключены:** продукт один — все функции (оформление, стикеры, скидки, каналы, интеграции и т.д.) включены по умолчанию. Переменные `EDITION` и `VITE_EDITION` не нужны.

---

## 2. Порядок запуска сервисов

Рекомендуемый порядок: сначала инфраструктура, потом API, потом фронт (и при необходимости Celery).

| Шаг | Сервис        | Команда |
|-----|---------------|--------|
| 1   | Postgres + Redis | `docker-compose up -d postgres redis` (или локальные сервисы уже запущены) |
| 2   | API (FastAPI) | В **корне проекта:** `poetry run uvicorn src.main:app --reload` |
| 3   | Frontend (dev) | В каталоге **frontend:** `npm run dev` |
| 4   | Celery (опционально) | В корне: `poetry run celery -A src.infrastructure.messaging.celery_app worker -l info` |

После этого:

- **API (Swagger):** http://localhost:8000/docs  
- **Health:** http://localhost:8000/health  
- **Сайт (фронт):** http://localhost:5175 — порт задан в `frontend/vite.config.ts` (server.port: 5175). Если меняли — смотрите вывод `npm run dev`.

---

## 3. Перезапуск

- **Только API:** остановите uvicorn (Ctrl+C) и снова выполните  
  `poetry run uvicorn src.main:app --reload`
- **Только фронт:** в каталоге `frontend` остановите dev-сервер (Ctrl+C) и снова:  
  `npm run dev`
- **БД/Redis в Docker:**  
  `docker-compose restart postgres redis`
- **Всё в Docker (если используете):**  
  `docker-compose down` затем `docker-compose up -d`

### Перестройка билдеров без кэша и перезапуск системы

Полная пересборка образов (api, celery, celery-beat) без кэша и подъём всех сервисов:

```powershell
# В корне проекта d:\CURSOR\projects\dental_booking
docker compose down
docker compose build --no-cache
docker compose up -d
```

После `up -d` при необходимости снова примените миграции (если БД уже поднята и вы их выполняли с хоста — можно пропустить):

```powershell
poetry run alembic upgrade head
# либо из контейнера API:
docker compose run --rm api alembic upgrade head
```

**Если `build --no-cache` падает с SSL/сетевыми ошибками** (PyPI внутри Docker): повторите позже при стабильном интернете или соберите с кэшем: `docker compose build` затем `docker compose up -d`.

После изменения миграций всегда в корне проекта:

```powershell
poetry run alembic upgrade head
```

---

## 4. Сборка фронта (production)

В каталоге **frontend**:

```powershell
cd frontend
npm install
npm run build
```

Артефакты появятся в `frontend/dist/`. Предпросмотр собранного фронта:

```powershell
npm run preview
```

Если **npm run build** падал с ошибками TypeScript/ESLint — они исправлены в текущей кодовой базе (см. список правок ниже). После `git pull` или применения правок снова выполните `npm install` и `npm run build`.

---

## 5. Исправления, из-за которых падал build (для справки)

Чтобы сборка проходила без ошибок, были сделаны такие правки:

- **WaitlistPanel.tsx:** неиспользуемый параметр `date` переименован в `_date`; устранена возможность `null` при обращении к `prefs(entry)`.
- **AdminDashboardPage.tsx:** удалена неиспользуемая переменная `currentClinicId`.
- **AdminMarketingPage.tsx, AdminRecallPage.tsx:** у `EmptyStateHint` используется проп `title`, а не `message`.
- **AdminPrepaymentPage.tsx:** для `NumberInput` (дедлайн) в `onChange` передаётся `number | undefined` (приведение типа).
- **AdminRecallPage.tsx:** удалены неиспользуемые импорты и константа `CHANNELS`.
- **AdminWaitlistPage.tsx:** у `Select` (пациент) `onChange` приведён к виду `(v) => setPatientId(v ?? "")`.
- **useAdminWaitlist.ts:** неиспользуемый параметр `date` переименован в `_date`.

После этих правок `npm run build` выполняется успешно.

---

## 6. Чек-лист перед разработкой

- [ ] В корне: `poetry run alembic upgrade head`
- [ ] Postgres и Redis запущены
- [ ] В корне: `poetry run uvicorn src.main:app --reload`
- [ ] В `frontend`: `npm run dev`
- [ ] В браузере открыты http://localhost:8000/docs и страница приложения (порт из вывода Vite)
