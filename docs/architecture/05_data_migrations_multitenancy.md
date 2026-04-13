# Данные, миграции, мультитенантность

## Назначение

PostgreSQL как единственный источник правды по схеме; Alembic для эволюции; изоляция данных по клинике.

## Как это работает (жизненный цикл схемы и данных)

1. **Применение миграций:** в `docker-compose.yml` сервис `migrations` запускает `alembic upgrade head` до старта приложения. Локально то же самое вручную из корня проекта с корректным `DATABASE_URL`.
2. **Генерация ревизий:** разработчик сравнивает модели с БД через autogenerate; так как `alembic/env.py` подгружает все модули `src.domain.entities.*`, в diff попадают все таблицы, известные ORM.
3. **Рантайм ORM:** приложение не создаёт таблицы при старте — только миграции. Сессии работают с тем же DSN, что и Alembic (async).
4. **Тенант в запросах:** админский JWT содержит `clinic_id`; эндпоинты с `{clinic_id}` в path обычно сравнивают его с `admin.clinic_id` или с явным списком доступных клиник (логика в конкретном роутере). Пациент не получает `clinic_id` в `RequestContext`, поэтому фильтрация идёт через связь записи с пациентом/бронью.
5. **Реплика для отчётов:** чтение тяжёлых отчётов может идти через `get_reporting_session` на отдельный DSN (`DATABASE_REPLICA_URL`); запись и критичные операции — через primary `get_session`.

## Alembic

- Конфигурация: `alembic/env.py`.
- URL БД: `settings.database_url` из `src/core/config.py` (async, драйвер asyncpg в типичном compose).
- `target_metadata`: `Base.metadata` из `src/infrastructure/database/base.py`.
- Подтягивание всех таблиц: цикл `pkgutil.iter_modules` по `src.domain.entities` с `__import__` каждого модуля (кроме `__init__`), чтобы autogenerate и squash видели полную схему.
- Таблица версий: `alembic_version`, колонка `version_num` (тип `String(128)`).

Ревизии: каталог `alembic/versions/`.

## Мультитенантность (модель)

- Основной столбец изоляции в домене: `clinic_id` на сущностях клиники и связанных записях (пациенты, брони, омни и т.д.).
- Омниканал: сущности `omni_*`; HTTP-префикс `/owner/` в API не задаёт отдельного типа пользователя в БД — см. `owner_omni_channels.py` и [backend/api_layer.md](./backend/api_layer.md).
- RBAC и JWT: клиника в токене админа должна совпадать с выбором в UI (`API_STORAGE_KEYS.adminClinicId` на фронте).

## Связь domain → infrastructure

- Репозитории: интерфейсы в `src/domain/interfaces/repositories/`, реализации в `src/infrastructure/database/` (и смежные модули).
- Не каждая сущность обязана иметь выделенный класс репозитория; часть запросов может жить в сервисах.

## Статус

- Миграции и импорт metadata: реализовано.
- Доказательство изоляции: тесты вроде `tests/api/test_tenant_isolation_admin_paths.py`.

## Непонятное

Политика soft-delete и каскадов — только по чтению конкретных моделей и миграций.

**Backup / BCP (не путать с Alembic):** политика кластерного backup и runbook восстановления — [09_backup_restore_bcp.md](./09_backup_restore_bcp.md), [ADR-008](../adr/ADR-008-backup-restore-bcp.md), [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md).

### Enterprise-аудит (честная оценка)

- **Критические риски:** нет строки данных и миграций для **platform-tenant** (оператор SaaS) и self-service создания нового клиента; текущая схема — клиники и опционально `Organization` под сеть клиник, не вендор платформы ([INDEX.md](./INDEX.md), [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md)).
- **Средние риски:** изоляция без RLS — зависимость от тестов и code review каждого запроса.
- **Формально / недоделано:** стратегия zero-downtime для тяжёлых миграций не описана в этом каталоге.
- **Рекомендуемые доработки:** ADR на tenant; при введении platform-слоя — отдельная схема или строгие policy + аудит миграций.

### Соответствие фактам (проверка)

- `alembic/env.py`, `Organization`, `Clinic` — статическое чтение; прогон миграций в рамках аудита документа не выполнялся.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** без RLS ошибка в одном запросе — потенциальный cross-tenant leak; компенсация — тесты и ревью.
- **Что усилить:** стратегия zero-downtime для тяжёлых миграций (ONLINE, batched backfill).
- **С нуля:** outbox-таблица при внедрении надёжных событий ([U-007](./UNRESOLVED_AND_CONFUSION_LOG.md)); RLS — по ADR.
- **БД:** см. [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) §3.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).
