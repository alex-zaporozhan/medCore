# Демо: учётные записи multi-tenant showcase

> **Только для локального / закрытого стенда.** Пароли и почты `@showcase-mt.demo` не использовать в продакшене.

Порядок вместе с образами для VPS: **`documentation/VPS_IMAGE_AND_DATA.md`**.

## Если «не входит ни на один логин»

1. **В БД нет пользователей, пока не выполнены сиды.** После `alembic upgrade head` таблицы пустые. Обязательно по порядку:
   - `poetry run python -m src.scripts.seed_rbac_baseline`
   - `poetry run python -m src.scripts.seed_multi_tenant_showcase`  
   Если скрипт пишет `already applied`, а вы чистили БД вручную — сделайте полный сброс тестовой БД и снова `upgrade head` + оба сида.
2. **Куда заходить:** админка клиники — страница **входа сотрудников** (`/admin/login`), запрос `POST /api/v1/admin/auth/login`. Это **не** вход пациента по телефону и **не** кабинет Основателя платформы (`/platform/...`).
3. **Пароль не короче 8 символов** (у демо пароль длиннее — копируйте целиком, без пробела в конце строки).
4. **Фронт и API:** в разработке запускайте API (`uvicorn` на **8000** или Compose на **8010**) и фронт **`npm run dev`** (порт **5175**). Vite проксирует `/api` на живой API: сначала host **8000**, если он отвечает `/health`, иначе Compose **8010**. Override: `VITE_API_PROXY_TARGET`. Для **`npm run preview`** (порт **4173**) тот же прокси. Не оставляйте `frontend/vite.config.js` — Vite на Windows возьмёт его вместо `.ts`.
5. **Проверка без браузера** (подставьте хост/порт своего API; PowerShell — кавычки как ниже):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/admin/auth/login -H "Content-Type: application/json" -d "{\"email\":\"owner.kazan@showcase-mt.demo\",\"password\":\"ShowcaseMT2026!\"}"
```

Ожидается JSON с `access_token`. При **неверном пароле** API возвращает `401` с `code: invalid_credentials` и английским `detail`; экран логина показывает текст из i18n (`Неверный email или пароль` / `Invalid email or password`). Если пароль верный, а вход всё равно не проходит — почти всегда **этого email нет в таблице `admins`** (сиды не гоняли или другая база в `DATABASE_URL`).

6. **Другой набор демо:** тяжёлое моно-демо — `seed_presentation_showcase` → логины `admin@dentapro.demo` / `manager@dentapro.demo`, пароль **`Presentation2026!`** (см. **`documentation/CREDENTIALS_REFERENCE.md`**). Не смешивайте с multi-tenant без осознанного сброса БД.

---

После `alembic upgrade head` выполните:

```bash
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

### Миграции схемы (Alembic) — от нуля до head

1. **PostgreSQL запущен**, в `.env` (или переменных окружения) задана **`DATABASE_URL`** на вашу БД (пример в **`.env.example`**; порт часто `5442` при `docker-compose`).
2. **Создать пустую БД** (один раз), если её ещё нет — из `psql` под суперпользователем, например:  
   `CREATE DATABASE dental_booking OWNER postgres;`
3. **Зависимости:** из корня репозитория  
   `poetry install`
4. **Накатить все ревизии до последней:**  
   `poetry run alembic -c alembic.ini upgrade head`  
   Проверка: в таблице `alembic_version` одна строка с ревизией `head` (при необходимости: `SELECT * FROM alembic_version;`).
5. **Данные демо (не миграции):**  
   `poetry run python -m src.scripts.seed_rbac_baseline`  
   `poetry run python -m src.scripts.seed_multi_tenant_showcase`  
   При необходимости дослить слой Commerce/Kanban/календарь:  
   `poetry run python -m src.scripts.backfill_showcase_saas_extras`

**Новая ревизия после правок моделей:**  
`poetry run alembic revision --autogenerate -m "краткое описание"` — вручную проверить сгенерированный файл, затем снова `upgrade head`.

**Если при backfill / сиде была ошибка `NoReferencedTableError` (нет таблицы `payments` или `products`):** в `showcase_saas_extras` должны быть side-effect импорты `Payment` и `Product` (регистрация FK в metadata). Обновите репозиторий и повторите команду.

**Windows / PowerShell:** переменная среды `DATABASE_URL`, заданная вручную в сессии, перекрывает значение из `.env` — возможен `InvalidPasswordError` при верном пароле в файле. Выполните `Remove-Item Env:DATABASE_URL` и снова `alembic` / сиды. Аналогично: при `TESTING=1` сиды падают с `'NoneType' object is not callable` на `AsyncSessionLocal` — сбросьте `Remove-Item Env:TESTING`.

**Ошибки asyncpg про «offset-naive and offset-aware»** на демо-слое: колонки без timezone; в скрипте для них используются naive UTC-времена (`_utc_naive_wall`).

### Клиника, организация SaaS и баннер Commerce

- У каждого админа всегда есть **`clinic_id`** (контекст клиники и расписания).
- Отдельно задаётся **`organization_id`** (SaaS: сеть клиник, entitlements, экран Commerce). Сообщение «Нет организации» означало отсутствие **`organization_id`** в сессии/API, а не отсутствие привязки к клинике.
- Если showcase накатывали старым сидом:  
  `poetry run python -m src.scripts.backfill_showcase_saas_extras`  
  (подтянет org у админов, Commerce, **календарь записей пациентов** на 3 месяца ~65% слотов, **уплотнение ±14 дней** на английском, **Kanban** включая поток Sales и due dates в окне, **календарь сотрудников** + встречи окна, **ленту**, чаты, витрину, логин роли `doctor`). После этого **перелогиньтесь**.

### Уже залитая БД без демо-слоя

```bash
poetry run python -m src.scripts.backfill_showcase_saas_extras
```

Далее: **перелогин** в админке; при «залипании» сетки расписания убедитесь, что Redis доступен (скрипт сбрасывает ключи `schedule:*` best-effort).

### Пересоздать только слой записей пациентов (bookings showcase)

Осторожно в общей БД: удаляйте только если нет зависимостей (у демо-слоя обычно нет связанных платежей).

```sql
DELETE FROM bookings WHERE notes = 'showcase_calendar_v1';
```

Затем снова:

```bash
poetry run python -m src.scripts.backfill_showcase_saas_extras
```

Идемпотентные маркеры для ручной чистки (каскады и FK — в схеме БД). **Новые** строки сида **без** слова Demo в title: Kanban/календарь/лента/huddle — канонические английские заголовки. Legacy (старые БД): `title LIKE 'Демо Kanban:%'` / `'Demo Kanban:%'` / `'Demo window:%'`; события `'Демо календарь:%'` / `'Demo calendar:%'` / `'Demo window cal:%'`; huddle `'Demo huddle:%'` или title `Two-week ops`. Bookings: `notes IN ('showcase_calendar_v1', 'en_demo_window_v1')`.

Канон для QA: **`docs/artifacts/QA_ARCH_SHOWCASE_DEMO_LAYER.md`**.

Один пароль для всех перечисленных админских пользователей:

`ShowcaseMT2026!`

Роли в продукте: **владелец** — глобальная роль `owner`; **администраторы** — `admin`; **маркетологи** — глобальная роль `manager` (в матрице прав есть маркетинг и широкий операционный доступ).

Учётная запись **Основателя платформы** этим сидом не создаётся: `poetry run python -m src.scripts.create_platform_founder_user --email ... --password ...`.

## Владельцы (owner)

| Город / юрлицо (ключ email) | Отображаемая клиника | Email |
|-----------------------------|----------------------|-------|
| Austin, TX (`kazan`) | Brightside Dental — Austin | owner.kazan@showcase-mt.demo |
| Boston, MA (`nizhny`) | Harbor Smile — Boston | owner.nizhny@showcase-mt.demo |
| Lyon (`samara`) | Clinique Dentaire Lumière — Lyon | owner.samara@showcase-mt.demo |
| Milan (`krasnodar`) | Studio Dentale Aurora — Milan | owner.krasnodar@showcase-mt.demo |
| Chicago, IL (`rostov`) | Lakeshore Family Dental — Chicago | owner.rostov@showcase-mt.demo |

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

## Врач (роль `doctor`, не карточка врача в расписании)

Узкий RBAC: задачи, медкарта, staff chat. Нет payroll / CRM / Omni inbox. Отображаемое имя **Hannah Cole, DDS** — отдельно от chair-врачей (Paul Brennan / Mary Ellis / Ben Carter).

| Email |
|-------|
| doctor1.kazan@showcase-mt.demo |
| doctor1.nizhny@showcase-mt.demo |
| doctor1.samara@showcase-mt.demo |
| doctor1.krasnodar@showcase-mt.demo |
| doctor1.rostov@showcase-mt.demo |

## Пароль (все строки выше)

`ShowcaseMT2026!`

Повторная генерация таблицы из кода:

```bash
poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials
```
