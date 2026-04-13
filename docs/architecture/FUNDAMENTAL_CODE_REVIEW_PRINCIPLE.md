# Фундаментальный обзор кода и БД (PRINCIPLE)

> **Назначение:** углублённый взгляд на логику, границы транзакций, данные и пробелы продукта. Опора на чтение репозитория, без претензии на полный penetration-test или аудит прод-окружения.  
> **Связь:** [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md), [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md), [domains/booking_event_chain.md](./domains/booking_event_chain.md).  
> **Приёмка LEAD и бэклог P0–P2:** [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).  
> **Целевая платформа:** [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md). **ADR:** [../adr/README.md](../adr/README.md).

## 1. Методология

**Что анализировалось:**

- Слои API → application → domain → infrastructure (`src/`), точечно `payment_service`, `booking` entity, обработчики в `src/application/events/`.
- Мультитенантность и сущности: `Organization`, `Clinic`, `Payment`, индексы в моделях.
- Паттерн сессий БД: `get_db` в запросе vs `AsyncSessionLocal` в event handlers и Celery.

**Вне явного scope этого документа:**

- Полный перебор всех ~465 `*.py` и сценариев UI.
- Нагрузочное тестирование, `EXPLAIN` на прод-объёмах, проверка фактической настройки Prometheus в облаке.
- Юридический/медицинский compliance (только инженерные намёки).

---

## 2. Критические темы логики

### 2.1 Транзакции HTTP и отдельные транзакции обработчиков событий

**Факт:** обработчики в `src/application/events/` (например `lead_event_handlers.py`, `erp_event_handlers.py`) после `event_bus.publish` выполняются в **новых** сессиях (`async with AsyncSessionLocal() as session` или явный `begin()`).

**Следствие:** успешный `commit` HTTP-запроса **не** гарантирует успех всех side-effects: хендлер может упасть после коммита; два хендлера на одно событие не атомарны друг с другом. Порядок подписчиков фиксирован списком, но отказ одного не откатывает уже выполненный другой (в `EventBus.publish` ошибки изолируются).

**Риск:** «частично применённая» бизнес-цепочка (booking обновлён, ERP/лид нет) при сбоях или багах в хендлере.

**Направления усиления (без готовой реализации в этом документе):** transactional outbox в той же БД, что и основная запись; публикация в брокер; идемпотентные consumer’ы с ключом события; компенсирующие транзакции там, где деньги и отчётность.

### 2.2 In-process EventBus и масштабирование API

**Факт:** `src/application/events/event_bus.py` — глобальный объект в памяти процесса.

**Следствие:** при нескольких репликах uvicorn событие, опубликованное на реплике A, **не** видно на B; повтор запроса к другой реплике ведёт к другому поведению, если логика зависела от побочных эффектов события в том же процессе.

**Направление:** вынести критичные цепочки в очередь (Celery уже есть для части задач) или outbox + worker.

### 2.3 Платежи и webhook

**Файлы:** `src/application/services/payment_service.py` (`handle_webhook`), `src/domain/entities/payment.py`.

**Плюс:** `UniqueConstraint("provider", "provider_payment_id")` на `payments` снижает риск дубля строки платежа при повторных вставках на уровне БД.

**Поведение `handle_webhook` (по коду):** загрузка платежа по `provider_payment_id`, обновление статуса записи `Payment`, затем при `succeeded` переход брони из `PENDING` / `AWAITING_PAYMENT` в `CONFIRMED` и публикация `make_payment_success_event`. Повторная доставка webhook с тем же `succeeded` для уже подтверждённой брони **не** входит снова в ветку перехода (условие по `booking.status`), но **обновление** `payment_record` и метаданных провайдера выполняется при каждом вызове до этого — обычно идемпотентно по смыслу, но любое расширение веток требует явной проверки идемпотентности.

**Риск:** отсутствие внешнего идемпотентного ключа на уровне HTTP webhook (например заголовок/dedup по сырому телу) — при сомнении полагаются на идемпотентность YooKassa и на логику сервиса; стоит зафиксировать в ADR и тестах сценарий «двойной webhook».

### 2.4 Статусы бронирования

**Файл:** `src/domain/entities/booking.py` — `BookingStatus` с большим набором значений (включая legacy-совместимые строки в комментариях).

**Риск:** рассинхрон между `BookingStatusService`, API и фактическими строками в БД; сложность отчётов и инвариантов; ошибки в переходах при добавлении новых статусов.

**Направление:** единая документированная state machine (таблица допустимых переходов), тесты на запрещённые переходы, поэтапная уборка неиспользуемых значений через миграции данных (как этап, не DDL в этом документе).

---

## 3. База данных — направления улучшения (не готовые миграции)

| Тема | Суть |
|------|------|
| **RLS** | Сейчас изоляция по `clinic_id` — дисциплина приложения. Для Enterprise рассмотреть PostgreSQL RLS по `clinic_id` или централизованный policy-слой с аудитом всех запросов без фильтра. |
| **Organization** | `Clinic.organization_id` nullable; связь «сеть клиник» не сводится к модели platform-SaaS (см. U-004 в UNRESOLVED). Нужна продуктовая модель: кто создаёт организацию, как наследуются права. |
| **Индексы / отчёты** | Есть reporting DSN и `get_db_reporting`. Кандидаты на проверку планов запросов в эксплуатации: брони по `(clinic_id, appointment_date)`, omni-сущности по `business_account_id` — **не** утверждать отсутствие индекса без `EXPLAIN` на реальных данных. |
| **Outbox** | Новая сущность (идея): `id`, `aggregate_type`, `payload`, `created_at`, `published_at`, `attempts`, `last_error` — запись в той же транзакции, что и доменное изменение; воркер публикует в брокер или вызывает стабильные хендлеры. |

---

## 4. Что создать с нуля (продукт / инфраструктура)

- Контур **platform-operator** и self-service онбординг арендатора (см. [INDEX.md](./INDEX.md), U-004).
- **BFF** или иной слой для сессий без чувствительных токенов в `localStorage` (если цель — снизить XSS-риск).
- **Runbooks** в репозитории: backup/restore Postgres, отказ Redis, порядок миграций при даунтайме.
- **DLQ / метрики очередей** Celery, SLO на длину очереди.
- Явная **идемпотентность** webhook и критичных POST API (ключи в БД или Redis).

---

## 5. Сильные стороны (для баланса)

- Структурированные ошибки booking/payment, метрики, RBAC-матрица и тесты, реплика для чтения отчётов, уникальность платежа провайдера в схеме, развитый pytest по API и сервисам.

---

## 6. Связанные документы

- [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) — U-001–U-010, включая U-006 (webhook), U-007 (outbox), U-008 (CI), U-009 (BCP), U-010 (импорт).
- [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) — операционный перечень пробелов и жёсткая приёмка поверх этого фундаментального обзора.
- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), [../adr/README.md](../adr/README.md) — целевая модель и решения (platform, backup, outbox, импорт, webhook подписки платформы — ADR-011).
- Сводный обзор мастер-плана SaaS и корпуса по ответственности PRINCIPLE: [../artifacts/PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md](../artifacts/PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md).
- Модульные файлы в `docs/architecture/` — секция **Углубление (PRINCIPLE)** с узким фокусом по слою.

**Версия:** 2026-04-03

---

### Углубление (PRINCIPLE — фундаментальный обзор)

Этот файл **является источником** фундаментального разбора; остальные документы в `docs/architecture/` содержат сжатые секции со ссылкой сюда.

- **Сильные логические риски:** см. §2–§3 выше; приоритет — транзакции vs события, масштабирование bus, webhook, `BookingStatus`.
- **Что усилить:** при изменении `payment_service`, `event_bus` или схемы `payments`/`bookings` — обновить соответствующие § и [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md).
- **С нуля:** перечень в §4; каждый пункт требует ADR перед реализацией.
- **БД:** только направления в §3; конкретные миграции не входят в обязанности этого документа.
- **Полный разбор:** этот файл; модульные файлы — контекст по слоям.
