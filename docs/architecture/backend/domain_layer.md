# Слой Domain

Сущности: `src/domain/entities/` (более 130 модулей). Интерфейсы репозиториев: `src/domain/interfaces/repositories/`.

## Назначение

SQLAlchemy-модели таблиц и связей. Для Alembic в `alembic/env.py` импортируется весь пакет `src.domain.entities` через `pkgutil.iter_modules`, чтобы `Base.metadata` содержал полную схему.

## Как это работает (модели и контракты)

1. **Базовый класс:** все ORM-модели наследуют от `Base` (`src/infrastructure/database/base.py`, `DeclarativeBase`). Таблицы и колонки объявляются в модулях `src/domain/entities/*.py`.
2. **Связь с миграциями:** при `alembic revision --autogenerate` сравнивается текущая БД с `Base.metadata`; так как в `env.py` импортируются **все** подмодули `entities`, в metadata попадает вся схема, иначе autogenerate «не увидел бы» таблицы.
3. **Репозитории:** в `src/domain/interfaces/repositories/` задаются Protocol/ABC с методами вида `get_by_id`, `list_for_clinic`; **реализации** в `*_repo_impl.py` используют те же entity-классы и фильтруют по `clinic_id` там, где это правило домена (конкретика — в каждом файле impl).
4. **Мультитенантность на уровне данных:** большинство бизнес-таблиц содержат `clinic_id` (UUID); изоляция обеспечивается не магией ORM, а **явными фильтрами** в запросах сервисов и репозиториев. Пациентский JWT не несёт `clinic_id` в `RequestContext` (`dependencies.py` ставит `clinic_id=None`), поэтому привязка пациента к данным идёт через сущность `Patient` и её связи.
5. **Граница слоя:** domain-файлы не импортируют FastAPI; зависимость только на SQLAlchemy-типы и стандартную библиотеку (плюс uuid и т.д.).

## Группы сущностей (ориентир по именам)

- Клиника и персонал: `clinic`, `admin_user`, `organization`, `doctor`, `staff_profile`, календарь и лента staff.
- Запись и очереди: `booking`, `waitlist_entry`, связанные статусы.
- Пациент и медкарта: `patient_*`, `patient_medical_*`, диагнозы, файлы.
- Деньги: `financial_transaction`, `cashbox`, `wallet`, `wallet_transaction`.
- CRM: `lead_*`, пайплайн и стадии.
- Омниканал: `omnichannel_*`, `omni_*`, контакты, аудит.
- Задачи: `task`, `task_board`, `task_stream`, комментарии, теги.
- ERP-агрегаты: `erp_*_aggregate`, ведра отчётов, watermarks, audit refresh.
- RBAC: `role`, `permission`, `user_role`, гранты, аудит.
- Лояльность и подписки: `loyalty_*`, `subscription_*`, семейные связи.
- Формы: `digital_form_*`, токены ссылок, audit.
- **Commerce (Фаза 4, опция):** зарезервированные имена и границы — [domains/commerce_bounded_context.md](../domains/commerce_bounded_context.md); таблицы `commerce_*` не создавать до go по ADR-013.

## Мультитенантность

Опорный столбец изоляции данных в запросах — **`clinic_id`**. Сущность **`Organization`** группирует клиники (`Clinic.organization_id`); в комментарии к `Organization` указано, что строгая изоляция остаётся по клинике. Отдельной сущности **platform (вендор SaaS)** в домене нет. Детали — `docs/architecture/05_data_migrations_multitenancy.md` и [INDEX.md](../INDEX.md).

## Статус

- Metadata для миграций: реализовано.
- Соответствие «каждая сущность имеет repo»: нет; часть доступа через прямые запросы в сервисах.

## Непонятное

Полный перечень файлов сущностей — только из файловой системы каталога `entities/`.

### Enterprise-аудит (честная оценка)

- **Критические риски:** без RLS в БД изоляция целиком на дисциплине кода; регрессия в одном запросе может дать cross-tenant leak (см. тесты `test_tenant_isolation_*` как частичную защиту).
- **Средние риски:** `Organization` не задаёт автоматическую иерархию прав «сетевой владелец» в ORM.
- **Формально / недоделано:** enterprise SaaS с self-service созданием организаций не отражена в модели.
- **Рекомендуемые доработки:** ADR на tenant model; при multi-region — репликация и резервирование на уровне схемы.

### Соответствие фактам (проверка)

- `Organization`, `Clinic.organization_id`, комментарий в `organization.py` — проверено чтением entity-файлов.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** разросшийся `BookingStatus` и строки в БД — риск недопустимых переходов и отчётных аномалий (§2.4 фундаментального документа).
- **Что усилить:** единая матрица переходов в коде + тесты; `UniqueConstraint` на `payments` — сохранять при смене провайдера осознанно.
- **С нуля:** RLS по `clinic_id` при жёстких требованиях Enterprise.
- **БД:** проверка индексов под hot paths — только с `EXPLAIN` на реальных данных (§3).
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).
