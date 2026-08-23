# Справочник учётных записей и паролей (демо, сиды, инфраструктура)

> **Только для локальных стендов, презентаций и тестов.** В продакшене задайте собственные секреты; значения из этого файла не использовать.

Источники в репозитории: скрипты в `src/scripts/`, фикстуры `tests/conftest.py`, **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**, **`documentation/VPS_IMAGE_AND_DATA.md`**.

---

## 1. Multi-tenant showcase (5 клиник, RBAC)

**Запуск после миграций:**

```bash
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

| Параметр | Значение |
|----------|----------|
| **Единый пароль** для всех админских пользователей ниже | `ShowcaseMT2026!` |

**Почты** (полные таблицы по ролям): **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**.

Кратко: владельцы `owner.*@showcase-mt.demo`, админы `admin1|2.*@showcase-mt.demo`, маркетологи `marketing1|2.*@showcase-mt.demo`, узкая роль врача `doctor1.*@showcase-mt.demo` (города: kazan, nizhny, samara, krasnodar, rostov). После повторного сида — слой ±14 дней (календарь/Kanban/чаты) на английском; это seed, не Alembic.

Повторный вывод из кода:

```bash
poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials
```

**Основатель платформы** этим сидом **не создаётся** — только вручную (см. раздел 4).

---

## 2. Presentation showcase («Дентал Про», тяжёлое моно-демо)

**Запуск:** `poetry run python -m src.scripts.seed_presentation_showcase`  
(идемпотентность по `admin@dentapro.demo` / legacy `filial1@dentapro.demo`; см. docstring скрипта).

| Роль | Email | Пароль |
|------|-------|--------|
| Администратор (owner-роль в выводе скрипта) | `admin@dentapro.demo` | `Presentation2026!` |
| Менеджер | `manager@dentapro.demo` | `Presentation2026!` |

Контакты клиники в сиде: `info@dentapro.demo` (не обязательно пароль входа).

---

## 3. Базовый демо-сид (`seed_demo_data`)

Скрипт: `poetry run python -m src.scripts.seed_demo_data`

| Email | Пароль |
|-------|--------|
| `admin@example.com` | `admin12345` |

Создаётся при отсутствии админа у целевой клиники (логика в скрипте).

---

## 4. Основатель платформы (platform founder)

Готовой пары логин/пароль в репозитории **нет** — только команда создания:

```bash
poetry run python -m src.scripts.create_platform_founder_user --email <email> --password <пароль>
```

См. также `.env.example` (`PLATFORM_FOUNDER_JWT_SECRET`, MFA).

---

## 5. Автоматический сид для pytest (не для ручного входа на стенд)

Фикстура `seed_data` в **`tests/conftest.py`** при каждом прогоне создаёт клинику и пользователей с **случайными** email вида:

- админ: `admin-<hex>@test-clinic.local`
- врач: `doctor-<hex>@test-clinic.local`
- основатель: `pf-<hex>@test.platform.local`

| Пароль | Где используется |
|--------|------------------|
| `password123` | админ, врач, platform founder в тестовом сиде |

Пациентский вход в тестах — через `send-code` / Redis, не фиксированный пароль.

---

## 6. Инфраструктура по умолчанию (`.env.example` / docker-compose)

Сервисные учётные данные, **не** прикладные пользователи кабинета:

| Назначение | Пользователь | Пароль / примечание |
|------------|--------------|---------------------|
| PostgreSQL (локально в compose) | `postgres` | `postgres` (заменить в проде) |
| Имя БД по умолчанию | `dental_booking` / `dental_booking_test` | — |

Секреты приложения в примере: `SECRET_KEY`, `JWT_SECRET_KEY`, `PLATFORM_BILLING_WEBHOOK_SECRET` и др. — **плейсхолдеры**, задать свои.

---

## 7. Docker Hub / GitHub Actions

Публикация образов: логин и токен **только** в secrets репозитория (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`), не в `.env` в git. См. **`.github/workflows/docker-hub-publish.yml`** и **`CI_CD.md`**.

---

## Не получается войти

См. раздел **«Если не входит ни на один логин»** в **`documentation/DEMO_MULTI_TENANT_CREDENTIALS.md`**: чаще всего не выполнены сиды после миграций, открыт не тот экран входа (пациент / platform founder вместо `/admin/login`), или фронт не видит API (нет запущенного бэкенда или неверный порт).

## Быстрая навигация

| Сценарий | Документ / скрипт |
|----------|-------------------|
| Таблица всех email multi-tenant | `documentation/DEMO_MULTI_TENANT_CREDENTIALS.md` |
| VPS, образы, порядок миграций и сидов | `documentation/VPS_IMAGE_AND_DATA.md` |
| CI/CD и Hub | `CI_CD.md`, `AGENTS.md` |
