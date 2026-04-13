# Приёмка проекта (LEAD): жёсткая критика, пробелы и бэклог

> **Версия:** 2026-04-03 (ADR-пакет, BCP, gap scan)  
> **Статус:** операционный документ приёмки техлида; при расхождении с модульными файлами `docs/architecture/**/*.md` до их синхронизации **приоритет у этой версии** (см. [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md)).  
> **Рубрика и шкала:** [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md).  
> **Фундамент логики и БД:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).  
> **Паспорта SPA (объём, приоритеты, покрытие):** [../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md](../review/07_FRONTEND_PAGE_PASSPORT_SCOPE_AND_RISKS.md) · [../frontend/pages/README.md](../frontend/pages/README.md).

---

## Методология и границы честности

**Это не полный построчный аудит.** Репозиторий содержит порядка сотен файлов Python в `src/` и большой фронтенд; за один проход прочитать и проверить каждую строку нереалистично. Ниже зафиксировано, **что именно** опирается на чтение кода, **что** — на структуру каталогов и grep, **что** не проверялось.

| Категория | Что сделано |
|-----------|-------------|
| **Чтение кода (выборочно)** | `src/main.py` (health/replica, metrics), `src/infrastructure/database/base.py` (`get_db`, commit), `src/application/events/event_bus.py`, обработчики `lead_event_handlers.py`, `erp_event_handlers.py`, `loyalty_event_handlers.py`, `tasks_event_handlers.py` (паттерн `AsyncSessionLocal`), `src/application/services/payment_service.py` (`handle_webhook`), `src/api/v1/dependencies.py`, `src/api/v1/routers/owner_omni_channels.py`, `frontend/src/api/client.ts`. |
| **Структура и сигналы** | `.github/workflows` vs `workflows_disabled`, список `tests/**/*.py`, grep `TODO` в ключевых сервисах, наличие `package-lock.json`, отсутствие `uv.lock` в корне (по glob). |
| **Сверка с документацией** | Утверждения [INDEX.md](./INDEX.md), [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md), [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md), [08_tests_matrix.md](./08_tests_matrix.md). |
| **Вне scope** | Нагрузочные тесты, реальный прод-Prometheus, penetration test, юридический/медицинский compliance, полный обзор всех роутеров и всех React-страниц. |

Если утверждение ниже **без пути к файлу** — это вывод уровня «гипотеза для проверки», а не факт из кода.

---

## Вердикт в одном абзаце

Как **продукт с богатым доменом и серьёзной инженерной культурой внутри монолита** репозиторий **жизнеспособен**: широкий API, RBAC, тесты, метрики, реплика для чтения, осмысленное разделение слоёв. Как **позиционируемый «мультиарендаторный Enterprise SaaS» с гарантиями эксплуатации и поставки** проект **не дотягивает**: нет контура оператора платформы и self-service онбординга арендатора, изоляция тенанта только кодом (без RLS), доменные события in-process и в отдельных транзакциях от HTTP, горизонтальное масштабирование API ломает модель событий, токены админа/пациента в `localStorage`, критичные CI-пайплайны и сканирование зависимостей **лежат в `workflows_disabled`**, а webhook-платежей покрыт **дырявым** smoke-тестом без проверки идемпотентности. Документация в `docs/architecture/` в целом **честнее среднего** (явно говорит про `/owner/` и EventBus), но маркетинговое слово «Enterprise» без оговорок — **преувеличение**.

---

## Сильные стороны (с якорями)

- **Слои и объём логики:** `src/application/services/` — сосредоточение бизнес-логики; DTO и события отделены от сущностей; это видно по импортам в `payment_service.py`, `booking_service.py` и др.
- **RBAC и контекст запроса:** `src/api/v1/dependencies.py`, `RbacServiceImpl`, тесты в `tests/application/`, `tests/api/test_rbac_*` — зрелее типичного CRUD-проекта.
- **Наблюдаемость в коде:** `/metrics`, middleware длительности, счётчик `domain_event_handler_failures_total` в `src/application/events/event_bus.py`.
- **Чтение с реплики:** `get_db_reporting`, `AsyncSessionLocalReporting`, проба в `health_replica` — [ADR-005](README в `alembic` / упоминания в коде) отражено в фактах.
- **Платежи — схема:** `UniqueConstraint(provider, provider_payment_id)` в `src/domain/entities/payment.py` (см. FUNDAMENTAL) — правильное направление для идемпотентности строки.
- **Тесты:** десятки файлов в `tests/api/`, `tests/services/`, `tests/security/`, `tests/e2e/` — для внутреннего качества это **актив**, не декорация.
- **Документация:** INDEX/MASTER/FUNDAMENTAL явно фиксируют `/owner/` = `get_current_admin` и split-транзакции событий — это **не фантазия**, а соответствие коду (`owner_omni_channels.py`, `event_bus.py`, handlers).

---

## Критические находки (P0 / блокеры позиционирования или прод-риска)

1. **Нет platform-tenant и продукта онбординга SaaS-клиента** — изоляция и продуктовая модель «один вендор — много бизнесов» не закрыты; см. сущности `Organization` / `Clinic` и U-004. *Якоря:* `src/domain/entities/organization.py`, `clinic.py`, [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md).

2. **In-process EventBus + несколько реплик API** — событие не пересекает процессы; поведение системы зависит от того, на какой инстанс попал запрос. *Якоря:* `src/application/events/event_bus.py` (глобальный `event_bus`), U-007.

3. **HTTP-транзакция и побочные эффекты событий не атомарны:** `get_db` делает `commit` после успешного завершения зависимости (`src/infrastructure/database/base.py`); обработчики событий открывают **новые** сессии (`AsyncSessionLocal` / `begin()` в `lead_event_handlers.py`, `erp_event_handlers.py`, и т.д.). Частичное применение цепочки при сбое хендлера — **архитектурный факт**, не баг одной строки. *Якоря:* FUNDAMENTAL §2.1, `event_bus.py` (изоляция исключений между хендлерами).

4. **Токены в `localStorage` (admin + patient)** — при компрометации XSS уровень защиты ниже, чем у httpOnly-cookie + BFF. *Якорь:* `frontend/src/api/client.ts` (`API_STORAGE_KEYS`, `localStorage`).

5. **`/health/replica` отдаёт `error: str(exc)` в JSON при 503** — потенциальная утечка деталей инфраструктуры наружу (U-001). *Якорь:* `src/main.py` `health_replica`.

6. **Поставка: активен только workflow проверки markdown-ссылок; backend-ci, frontend-ci, e2e, security-trivy — в `workflows_disabled`.** Нельзя честно говорить, что «CI гарантирует зелёный main» без отдельного процесса вне репо. *Якорь:* `.github/workflows/` vs `.github/workflows_disabled/`. См. U-008.

7. **Webhook платежей: идемпотентность бизнес-шага опирается на ветвление по `booking.status` и обновление `Payment`; тест — только smoke с неизвестным `provider_payment_id`.** Нет явного набора тестов «двойной succeeded для реальной брони». *Якоря:* `payment_service.py` `handle_webhook`, `tests/api/test_payments.py`, U-006.

---

## Средние риски (P1)

- **Именование `/owner/`:** вводит в заблуждение относительно роли; фактически `current_admin.clinic_id` как `business_account_id` — `src/api/v1/routers/owner_omni_channels.py` (U-005).
- **`BookingStatus` и переходы:** большой набор значений, риск рассинхрона сервисов и отчётов (FUNDAMENTAL §2.4, `booking_status_service.py`).
- **Технический долг в сервисах:** явные TODO, например перенос потока в `BookingCompletionService` — `src/application/services/booking_service.py` (строка с `TODO (DEV_PROMPT_BKG_CORE_001)`); упрощения в `booking_completion_service.py` (cash/source, payroll).
- **UI-заглушки:** комментарии TODO по экспорту в `frontend/src/admin/pages/AdminOmniVaultPage.tsx`.
- **Celery:** вопрос полноты постановки задач из кода (U-003) — не перепроверялся в этом проходе целиком; остаётся зоной due diligence.
- **Зависимости Python:** в репозитории не обнаружен `uv.lock` (по glob); воспроизводимость билдов зависит от практики деплоя (pip-compile/poetry lock и т.д. — проверять отдельно).

---

## Низкий приоритет (P2) и шероховатости

- Расхождение ожиданий интегратора («owner» = сеть клиник) с реализацией — документационно смягчено в INDEX, но **в API всё ещё путь `/owner/`**.
- Отсутствие runbooks backup/restore в `docs/` — для Enterprise-претензии это дыра процесса, не обязательно кода.

---

## Документация vs реальность

| Утверждение (суть) | Документ | Вердикт | Комментарий |
|-------------------|----------|---------|-------------|
| `/owner/` не отдельный JWT, используется admin + `clinic_id` | INDEX, MASTER, RUBRIC | **Подтверждено** | `owner_omni_channels.py` строки 19–21, 83–86. |
| HTTP commit отдельно от транзакций event handlers | FUNDAMENTAL, MASTER | **Подтверждено** | `base.py` `get_db` commit; handlers с `AsyncSessionLocal`. |
| EventBus in-process | INDEX, MASTER, FUNDAMENTAL | **Подтверждено** | `event_bus.py`. |
| Playwright / e2e CI отключены | 08_tests_matrix | **Подтверждено** | `workflows_disabled/e2e.yml`. |
| «Широкое покрытие» тестами | MASTER, 08 | **Частично преувеличено как гарантия** | Много тестов есть, но **нет** активного CI на backend в `.github/workflows`; формулировку стоит всегда связывать с «локально / внешний CI». |
| Enterprise SaaS без оговорок | маркетинговый контекст вне репо | **Преувеличение** | По рубрике честная оценка большинства осей **0–1**; см. таблицу ниже. |

---

## Оценка по оси усиленной рубрики (сводка)

Полные чек-листы и новые оси — в [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md). Здесь — **итог по репозиторию** одной строкой на ось.

| Ось | Уровень | Доказательство (кратко) |
|-----|---------|---------------------------|
| 1. Идентичность и границы тенанта | **1** | `clinic_id` везде; нет platform-operator (см. INDEX). |
| 2. Жизненный цикл клиента SaaS | **0** | Нет self-service провижининга нового арендатора в коде. |
| 3. Безопасность и соответствие | **1** | JWT, RBAC; `localStorage` + U-001. |
| 4. Надёжность | **1** | Health, метрики; split tx/events; нет распределённого bus. |
| 5. Наблюдаемость | **1** | `/metrics`, алерты в `deploy/prometheus`; прод-стек вне репо. |
| 6. Операции | **1** | Alembic, compose; runbooks не в репо. |
| 7. Коммерция и биллинг (продукт) | **0** | Подписки на сам продукт не смоделированы; YooKassa — оплата пациента. |
| 8. Поставка и цепочка (CI/CD) | **0–1** | Активен только `documentation-markdown-links.yml`; остальное disabled — U-008. |
| 9. Модель угроз фронта | **1** | Документированные ключи в `client.ts`; CSP/httpOnly — не зафиксированы как политика в репо. |
| 10. Управление изменениями API | **1** | Префикс `/api/v1`; явного deprecation-процесса в коде не выделено. |
| 11. Непрерывность бизнеса (BCP) | **0** | Runbooks restore/DR в репо не найдены; `restore-drill.yml` disabled. |
| 12. Отраслевые требования (медицина) | **не оценивается** | Нет заявленной сертификации в репозитории. |

---

## Бэклог недоработок (нумерованный)

Приоритет: **P0** — блокер заявленной модели или прод-риска; **P1** — существенный долг; **P2** — улучшение.

| # | Приоритет | Слой | Суть | Якорь / трекер |
|---|-----------|------|------|----------------|
| B-1 | P0 | backend/product | Спроектировать и реализовать platform-tenant + безопасный онбординг или перестать позиционировать как классический SaaS | U-004 |
| B-2 | P0 | backend/arch | Outbox или брокер для критичных доменных цепочек; идемпотентные consumer’ы | U-007, FUNDAMENTAL |
| B-3 | P0 | backend | Согласовать модель «запрос + события»: компенсации, сага или transactional outbox | FUNDAMENTAL §2.1 |
| B-4 | P0 | frontend/security | Снизить ущерб от XSS: httpOnly-сессии или BFF (оценка трудозатрат) | `client.ts` |
| B-5 | P0 | ops/CI | Включить или заменить пайплайны из `workflows_disabled` **или** зафиксировать внешний CI в документации | U-008 |
| B-6 | P0 | backend | Тесты двойного webhook YooKassa по всем веткам статусов | U-006, `test_payments.py` |
| B-7 | P0 | backend | Убрать или замаскировать `error` в ответе `/health/replica` для prod | U-001, `main.py` |
| B-8 | P1 | API/naming | Переименовать или задокументировать `/owner/*` до уровня OpenAPI и внешних интеграторов | U-005 |
| B-9 | P1 | domain | State machine `BookingStatus` + тесты запрещённых переходов | `booking.py`, `booking_status_service.py` |
| B-10 | P1 | backend | Закрыть TODO в `booking_service` / `booking_completion_service` или завести задачи с владельцем | grep `TODO` в сервисах |
| B-11 | P1 | data | Оценка RLS по `clinic_id` для Enterprise | FUNDAMENTAL §3 |
| B-12 | P1 | docs/ops | Заполнить `DR_RUNBOOK.md` фактами drill и RPO/RTO среды; внедрить ADR-008 в инфраструктуре | [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), U-009 |
| B-13 | P2 | frontend | Реализовать или снять с витрины TODO экспорта Omni Vault | `AdminOmniVaultPage.tsx` |
| B-14 | P1 | ops/product | Импорт CRM v1: выбрать первый коннектор и сущности по U-010 | ADR-010, U-010 |
| B-15 | P0 | backend/arch | Зафиксировать ADR-007 fork (RLS vs policy) и план миграции JWT/platform | ADR-007, U-004 |

Дубликаты с [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) намеренно ссылаются на U-* вместо повторного описания.

---

## ADR-пакет и crash-review (LEAD)

**Статус:** в [docs/adr/README.md](../adr/README.md) зафиксированы ADR-007…011 со статусом **Proposed** — это не «принято навсегда», а согласованная основа для работ @ARCH с последующей проверкой.

**Crash-критерии приёмки ADR (минимум):**

1. **ADR-007:** нет противоречия с U-004; выбран и задокументирован fork RLS vs policy; super-admin отделён от `AdminUser` клиники на уровне модели угроз.
2. **ADR-008:** для целевого прод-окружения указан провайдер backup/PITR или явный отказ с компенсацией; в `DR_RUNBOOK.md` заполнены строки drill (дата, длительность) после первого учения.
3. **ADR-009:** схема outbox согласована с миграциями; критичная цепочка (например payment/booking) имеет тест на at-least-once delivery без дублей в доменных инвариантах.
4. **ADR-010:** зафиксирован v1 scope; закрыт U-010 продуктовым решением.

Пока критерии не выполнены, красные флаги [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) и строки P0 в этом файле остаются силой.

**Монолит vs сервисы:** целевая стратегия — модульный монолит + outbox/воркеры; распил — только по метрикам (см. [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) §6).

---

## Связанные документы

- [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) — U-001–U-010.  
- [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) — транзакции, платежи, БД.  
- [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md) — сводка для чтения сверху вниз.  
- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), [../adr/README.md](../adr/README.md), [./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).  
- [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) — единый план фаз, платформы Основатель/Владелец, тарифов, лендинга, observability, embed+Битрикс24+AI+RAG (**§24**).  
- [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) — ревью мастер-плана (QA_ARCH); выводы **встроены** в мастер-план 2026-04-04 (LEAD closure).
