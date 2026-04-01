# Миграции БД (Alembic) — для OPS и передачи клиенту

> **Архитектурный контекст:** целевые правила эволюции схемы (expand/contract, отдельный шаг upgrade, откат) — `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md` §4. Этот документ — **практические** шаги для текущего репозитория (Poetry, Docker, Alembic).  
> **Расширенная историческая схема Alembic** (если нужна): `docs/artifacts/archive/_outdated/ARCH_ALEMBIC_MIGRATIONS.md`.

---

## Принципы при росте сложности (zero-downtime / несколько инстансов)

1. **Expand → deploy → contract:** сначала миграция **добавляет** nullable-поля/новые таблицы и не ломает старый код; деплой приложения с кодом, который умеет **и старое, и новое**; затем отдельная миграция **убирает** старое, когда ни один инстанс не читает удаляемые колонки.
2. **Деструктивные изменения** (DROP COLUMN/TABLE, смена типа с потерей данных) — **отдельный** релиз после подтверждения @ARCH и бэкапа.
3. **Несколько реплик API:** все инстансы должны оставаться совместимыми с текущей схемой БД на время выката; избегать миграций, которые ломают старый код до полного переключения.
4. **Celery / workers:** при миграциях, меняющих формат задач или полей в БД, согласовать порядок: сначала миграция и код-совместимость, затем включение воркеров с новой логикой (конкретный порядок — в `DEV_PROMPTS` / ADR).
5. **Staging → prod:** прогон `upgrade head` на staging с тем же порядком миграций, что и на prod; при возможности — снимок БД или бэкап перед prod.
6. **Целевое состояние «10/10»:** вынести `alembic upgrade` в **отдельный управляемый шаг** релиза (job / runbook), а не только «при старте контейнера» — решает @LEAD/@OPS по готовности; до этого действует вариант 1 ниже.

---

## Как правильно делать миграции

### Создание новой миграции (autogenerate)

- **Docker:** должен быть запущен **только контейнер БД** (чтобы к нему можно было подключиться). Остальные сервисы не обязательны.
- **Где запускать:** на хосте, из корня проекта, **обязательно через Poetry** (иначе не будет asyncpg и других зависимостей проекта):
  ```bash
  # Не вызывайте alembic напрямую (alembic upgrade head) — используйте poetry run.
  # Убедитесь, что в .env указан правильный DATABASE_URL (хост и порт БД).
  # Если БД в Docker: порт 5442 (см. docker-compose ports для db).
  poetry run alembic revision --autogenerate -m "краткое_описание"
  ```
- Файл миграции появится в `alembic/versions/`. При необходимости поправьте `revision` (короткий ID ≤32 символов) и `down_revision`.

### Применение миграций и запуск приложения

- **Вариант 1 (рекомендуется, как в `docker-compose.yml`):** отдельный сервис **`migrations`** запускает `alembic upgrade head` **один раз** и завершается с кодом **0**; контейнер `backend` (и Celery) стартуют только после **успешного** завершения миграций (`depends_on: migrations: condition: service_completed_successfully`). Сам **uvicorn** при старте миграции **не** выполняет — см. `Dockerfile` / `src/main.py`. После добавления **нового файла** в `alembic/versions/` пересоберите образ бэкенда, иначе в контейнере не будет файла ревизии:
  ```bash
  docker compose build backend
  docker compose up -d
  ```
  Контейнер `dental_booking_migrations` в `docker compose ps` будет в статусе **Exited (0)** — это ожидаемо.

- **Вариант 2:** применить миграции вручную с хоста (БД при этом должна быть доступна, например только `db` запущен). Всегда через **poetry run**:
  ```bash
  docker compose up -d db
  poetry run alembic upgrade head
  docker compose up -d
  ```
  Тогда при старте бэкенда миграции уже применены. Образ всё равно нужно пересобрать (`build backend`), если в репозитории появились новые файлы миграций — иначе в контейнере их не будет при следующем `upgrade head` из контейнера.

**Итого:** создаём миграции при включённой БД (Docker: `db`), с хоста через `poetry run alembic`. После добавления миграций — `docker compose build backend`, затем `docker compose up -d` (сервис `migrations` снова выполнит `upgrade head` к актуальной голове). Отдельно образ других сервисов (frontend, celery) пересобирать не нужно, если меняли только миграции.

**После `build backend` нужно заново применять миграции?** `build` только обновляет образ. Сами изменения схемы в БД применяются при следующем `docker compose up -d`, когда отработает сервис **`migrations`** (или вручную: вариант 2). Если вы только пересобрали образ и **не** делали `up`, миграции в БД не обновятся.

---

## Если бэкенд падает (502 Bad Gateway)

- **Логи:** первым делом посмотрите вывод контейнера бэкенда:
  ```bash
  docker compose logs backend
  docker compose logs backend --tail 200
  ```
  В логах будет причина: ошибка при старте (импорт, миграции, подключение к БД/Redis) или исключение при обработке запроса.
- **Проверка сервисов:** убедитесь, что подняты БД и Redis (бэкенд от них зависит):
  ```bash
  docker compose ps
  docker compose up -d db redis
  docker compose up -d backend
  ```
- **Redis:** если Redis недоступен, расписание и кэш теперь не роняют бэкенд (работа без кэша). Остальные запросы не зависят от Redis напрямую. При повторяющихся 502 смотрите логи — там будет stack trace или сообщение об ошибке.

---

## Новая установка (пустая БД)

Для новой базы данных выполните один раз (с хоста — через Poetry):

```bash
poetry run alembic upgrade head
```

Это применит единственную базовую миграцию `schema_v2_initial` и создаст полную схему (все таблицы: клиники, врачи, записи, ERP, CRM, лояльность, бумалесс, омниканал и т.д.).

В Docker Compose миграции выполняет сервис **`migrations`** до старта `backend`, а не entrypoint uvicorn.

---

## Существующая БД с данными

Если у вас уже есть рабочая БД с данными и вы переходите на единую базовую ревизию:

1. Убедитесь, что схема в БД соответствует текущим моделям приложения (все нужные таблицы и колонки есть).
2. Пометить текущее состояние как применённую ревизию (без выполнения миграций):
   ```bash
   alembic stamp schema_v2_initial
   ```
3. Дальнейшие изменения схемы — только через новые миграции с `down_revision = "schema_v2_initial"` (или последующей ревизией).

Исторический разбор схемы: `docs/artifacts/archive/_outdated/ARCH_ALEMBIC_MIGRATIONS.md`.

---

## Первый администратор и админ для клиента

- **Демо-админ (логин `admin@example.com` / пароль `admin12345`):** после применения миграций один раз создайте демо-данные. **Важно:** скрипт должен писать в ту же БД, к которой подключается бэкенд.
  - **Если бэкенд запущен в Docker** — выполняйте seed из контейнера:
    ```bash
    docker compose run --rm backend python -m src.scripts.seed_demo_data
    ```
  - С хоста (если бэкенд тоже с хоста и в .env тот же `DATABASE_URL`):
    ```bash
    poetry run python -m src.scripts.seed_demo_data
    ```
  **Если логин не принимает:**  
  1) Создайте демо-данные из контейнера (команда выше).  
  2) Если админ уже есть, но пароль не подходит — сбросьте пароль (из контейнера, чтобы использовать ту же БД, что и бэкенд):  
     `docker compose run --rm backend python -m src.scripts.reset_admin_password --email admin@example.com --password admin12345`  
  Пароль вводите без пробелов, ровно 8 символов: `admin12345`.

- **Свой логин и пароль для клиента:** скрипт создаёт одного админа с указанными email и паролем (пароль ≥ 8 символов). Нужна хотя бы одна клиника в БД (например, после `seed_demo_data` или созданная вручную):
  ```bash
  poetry run python -m src.scripts.create_admin --email client@company.com --password "SecurePass123"
  poetry run python -m src.scripts.create_admin --email admin@client.ru --password "Пароль123" --full-name "Иван Админов"
  ```
  В Docker:  
  `docker compose run --rm backend python -m src.scripts.create_admin --email client@company.com --password "SecurePass123"`

  После первого входа в админку можно создавать других администраторов через раздел «Администраторы» (API: `POST /api/v1/admin/admins`).

- **Большая демо-база для своих тестов (не для клиента):** скрипты в `src/scripts/dev/` заполняют данные за прошлый месяц (оплаты, визиты, скидки, отчёты) и записи на 2 недели вперёд. Подробно: `docs/DEV_DEMO_SCRIPTS.md`. Перед продом эти скрипты не запускать.

---

## Ошибка `DuplicateTableError: relation "clinics" already exists` при `alembic upgrade`

База уже содержит таблицы (например, поднята через `Base.metadata.create_all` или восстановлен дамп), а в `alembic_version` **нет** записи или она не соответствует схеме. Тогда Alembic считает, что нужно применить цепочку с нуля и падает на первом `CREATE TABLE`.

**Варианты:**

1. **Пустая тестовая БД:** удалить БД и создать заново, затем `poetry run alembic upgrade head` (или `python scripts/upgrade_test_db.py` с `DATABASE_URL_TEST`).
2. **Схема уже соответствует какой-то ревизии:** выставить маркер вручную, затем догнать голову:
   ```bash
   poetry run alembic current
   poetry run alembic history
   # подобрать revision, соответствующий фактической схеме, затем:
   poetry run alembic stamp <revision_id>
   poetry run alembic upgrade head
   ```
3. Не смешивать **разные** `DATABASE_URL`: убедиться, что в `.env` для `alembic` и для приложения указана одна и та же БД (или явно подставляйте `DATABASE_URL` при вызове Alembic).

---

## Стандарт ревизий

- Все новые миграции имеют короткий `revision` ID (≤32 символов), например `feat_xxx_short`.
- Одна голова: для новой установки только одна базовая миграция; следующие миграции строятся поверх неё.
- **`downgrade()`** обязателен по политике проекта (`docs/ROLE_ARCH.md`); для необратимых data-migration в downgrade документируется «best effort» или no-op с предупреждением в ревью @ARCH.
- При **двух головах** ветки Alembic (параллельные ветки разработки) — перед релизом **слить** в линейную цепочку (`merge revision`), иначе `upgrade head` на проде будет неоднозначным.

---

## Чеклист перед релизом с миграцией

- [ ] Миграция согласована с паспортом §4 (expand/contract, если применимо).
- [ ] Есть план отката: откат кода и/или `downgrade` на тестовой копии БД.
- [ ] Бэкап prod (или политика облака) перед деструктивным шагом.
- [ ] Образ `backend` пересобран после добавления файлов в `alembic/versions/`.
- [ ] На staging выполнен `upgrade head` без ошибок.

---

## ERP витрины (payroll / materials / ROI)

После ревизии `m8n9o0p1q2r3_erp_vitrines_payroll_materials_attribution` ночной job `erp_tasks.refresh_erp_aggregates_nightly` заполняет четыре витрины (выручка, payroll, дневной склад, атрибуция). Ревизия `n0o1p2q3r4s5_erp_payroll_aggregate_null_flags` добавляет флаги NULL для границ периода в `erp_payroll_aggregate` (корректный round-trip экстремальных дат). Отключить чтение из витрин и ходить только в сырой SQL: `ERP_REPORTS_READ_FROM_AGGREGATE=false`. Ручной пересчёт: `POST /api/v1/admin/clinics/{clinic_id}/reports/erp-aggregates/refresh` с телом `{"kind":...}` — нужны `erp.owner_reports.read`; для `kind` `attribution` или `all` дополнительно `attribution.reports.read`. См. `ARCH_DEV_ERP_VITRINES_026.md`.

Ревизия `o1p2q3r4s5t6_tasks_trace_id` добавляет nullable `tasks.trace_id` (индекс) для корреляции системных задач с логами/цепочками (`OBS_CHAINS_023` B4).

Ревизия `p2q3r4s5t6u7_manual_audit` создаёт `erp_aggregate_manual_refresh_audit` — журнал ручных `POST .../erp-aggregates/refresh` (admin, kind, диапазон, счётчики строк).

Ревизия **`q3r4s5t6u7v8_erp_coverage_watermark`** добавляет таблицу **`erp_aggregate_coverage_watermark`** (покрытие диапазона refresh по виду витрины; основа для **`trust_empty_if`** на read-path). Порядок деплоя: применить миграцию до включения кода, который читает watermark (обычно один релиз с бэкендом).

**Фоновый refresh по событию завершения визита (опционально):** переменные **`ERP_AGGREGATE_EVENT_REFRESH_ENABLED`** (по умолчанию `false`), **`ERP_AGGREGATE_EVENT_DEBOUNCE_SECONDS`** — см. `.env.example`. Требуются **Redis** (debounce) и **Celery worker** с задачей `erp_tasks.refresh_clinic_erp_aggregates_window`. Детали — `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` §6.2.

**Выборочная сверка сумм visit_revenue (опционально):** **`ERP_AGGREGATE_PARITY_SAMPLE_ENABLED`** (по умолчанию `false`) — ежедневная задача `erp_tasks.run_daily_visit_revenue_parity_sample` (Celery beat **05:15 UTC**, после nightly). Метрика и алерт — `NONFUNCTIONAL_AUDIT_NEXT.md` §5.2.

Ревизия **`w5perf1idx_fin`** (Wave 5 / QA_ARCH A3): частичные индексы по `type='income'` для `financial_transactions` и индекс `(clinic_id, period_start, period_end)` для `salary_transactions`. Опциональные env: **`DATABASE_REPLICA_URL`**, **`DB_REPORTING_STATEMENT_TIMEOUT_MS`**, **`DB_REPLICA_LAG_WARN_SECONDS`**, **`ERP_DASHBOARD_CACHE_ENABLED`**, **`ERP_DASHBOARD_CACHE_TTL_SECONDS`** — см. `docs/adr/ADR-005-wave5-replica-reporting-redis-cache.md`, `docs/artifacts/WAVE5_OPS_RUNBOOK.md`, `NONFUNCTIONAL_AUDIT_NEXT.md` §5.3. Пример **EXPLAIN** после применения: `docs/artifacts/WAVE5_A3_EXPLAIN_QUERIES.sql`.

Ревизия **`r4s5t6u7v8w9`** (Wave 3 CRM/Loyalty): таблицы **`loyalty_groups`**, **`lead_secondary_bookings`**, **`crm_lead_estimated_value_audit`**; nullable **`family_links.group_id`**. Runbook групп: `docs/artifacts/LOY_FAMILY_LOYALTY_GROUP_MIGRATION_RUNBOOK.md`. Задача Celery **`crm_tasks.reconcile_lead_actual_values`** — периодическая сверка лидов `success` с нулевым фактом (по согласованию с OPS, beat не включён по умолчанию).
