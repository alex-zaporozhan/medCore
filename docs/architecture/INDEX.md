# Архитектура репозитория — детальная карта

> **Вход для RAG / @QA_ARCH фаза 3:** цепочка «истина → обзор → деталь»: код и тесты → [`../product_state/INDEX.md`](../product_state/INDEX.md) (слой S) → этот файл → зоны SPA [`../frontend/FRONTEND_ARCHITECTURE_CANON.md`](../frontend/FRONTEND_ARCHITECTURE_CANON.md). Порядок слоёв и конфликты: [`../RAG_CANON.md`](../RAG_CANON.md), карта `docs/`: [`../DOC_TOPOLOGY.md`](../DOC_TOPOLOGY.md).

> **Версия:** 2026-04-10 (**§31** мастер-плана SaaS — огибающая масштаба и @ARCH; отчёт [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](./ENTERPRISE_SAAS_SCALE_ENVELOPE.md)) · 2026-04-09 (якоря §15, §25–§30) · 2026-04-03 (QA_ARCH: рубрика Enterprise)  
> **Генеральный обзор (все 18 модулей + SaaS-выводы в одном файле):** [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md)  
> **Назначение:** пошаговое, привязанное к коду описание слоёв, модулей и инфраструктуры. Краткая сводка и mermaid-схема — в [../product_state/ARCHITECTURE_FROM_CODE.md](../product_state/ARCHITECTURE_FROM_CODE.md).  
> **Рубрика критики Enterprise SaaS:** [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) (оси, шкала 0–2, системные выводы по коду).  
> **Рубрика фронтенда (макро/микро, матрица UI↔API, итерации A/B/C):** [ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md](./ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md).  
> **Канон зон SPA, данные, компонентные правила:** [../frontend/FRONTEND_ARCHITECTURE_CANON.md](../frontend/FRONTEND_ARCHITECTURE_CANON.md) · **слои и трассируемость фронта:** [../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md) · критерии паспорта экрана: [../frontend/PAGE_PASSPORT_CRITERIA.md](../frontend/PAGE_PASSPORT_CRITERIA.md) · каталог паспортов: [../frontend/pages/README.md](../frontend/pages/README.md).  
> **TARGET (якорь Phase 0 / 0-F3):** [ENTERPRISE_SAAS_TARGET.md](./ENTERPRISE_SAAS_TARGET.md).  
> **Фундаментальный обзор логики, транзакций и БД:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).  
> **Приёмка LEAD, жёсткая критика и бэклог пробелов:** [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).  
> **Эталон целевой платформы (multi-tenant, super-owner):** [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).  
> **Envelope масштаба (§31, черновик):** [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](./ENTERPRISE_SAAS_SCALE_ENVELOPE.md).  
> **ADR (решения platform, backup, outbox, импорт):** [../adr/README.md](../adr/README.md).  
> **Мастер-план масштабирования под SaaS (Основатель, Владелец, тарифы, лендинг, 2FA, observability):** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md).  
> **@ARCH: поэтапный архитектурный план исполнения МП (папка, MASTER + фазы + порядок для @DEV):** [arch_plan/README.md](./arch_plan/README.md) · [arch_plan/MASTER_ARCH_PLAN.md](./arch_plan/MASTER_ARCH_PLAN.md) · **порядок работ @DEV:** [arch_plan/DEV_EXECUTION_SEQUENCE.md](./arch_plan/DEV_EXECUTION_SEQUENCE.md) · **долг полного закрытия фаз (сверх DoD):** [arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).  
> **LEAD: цикл реализации по эпик-срезам (ARCH → DEV → QA_ARCH, шаблоны промптов):** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](./LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md).  
> **Индекс эпик-срезов SaaS (traceability DOC-1):** [SAAS_EPIC_TRACEABILITY_INDEX.md](./SAAS_EPIC_TRACEABILITY_INDEX.md) · приоритет 1a vs 1b: [SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md](./SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md).  
> **OPS smoke observability (OBS-1):** [../operations/OBSERVABILITY_COMPOSE_SMOKE.md](../operations/OBSERVABILITY_COMPOSE_SMOKE.md).  
> **LEAD: Switch Plan Mode — Фаза 0 SaaS (первый узел §15, корпус ADR/gap перед 1a):** [LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md](./LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md).  
> **Мастер-план — расширения LEAD §25–§31 (импорт, магазин, антиспам, security/DevTools, бренд МойКлиент, монолит, **огибающая масштаба**):** [§25](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-25) · [§26](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-26) · [§27](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-27) · [§28](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-28) · [§29](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-29) · [§30](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-30) · [§31](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-31) · дорожная карта и mermaid (**вкл. Фазу 4**): [§15](./SAAS_STRENGTHENING_MASTER_PLAN.md#saas-sec-15).  
> **LEAD: пресеты и цены РФ (первый выход):** [LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md](./LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md) — дополняет мастер-план.  
> **Embed / §24 (Phase 1e):** [EMBED_WIDGET_INTEGRATION.md](./EMBED_WIDGET_INTEGRATION.md).  
> **Операции релиза и SLO:** [../operations/RELEASE_CHECKLIST.md](../operations/RELEASE_CHECKLIST.md), [../operations/SLO_CRITICAL_PATHS.md](../operations/SLO_CRITICAL_PATHS.md), [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), [../operations/FOUNDER_ACCESS_BREAKGLASS.md](../operations/FOUNDER_ACCESS_BREAKGLASS.md), [../operations/TENANT_OFFBOARDING_AND_EXPORT.md](../operations/TENANT_OFFBOARDING_AND_EXPORT.md), **§17.1 мультиреплика + webhook B / signup:** [../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md).
> **Платформа / PII / ошибки платежей:** [PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md](./PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md), [PLATFORM_BILLING_ERROR_CATALOG.md](./PLATFORM_BILLING_ERROR_CATALOG.md), [API_PUBLIC_ERROR_CODES.md](./API_PUBLIC_ERROR_CODES.md) (единый `code` в JSON), [API_VERSIONING_POLICY.md](./API_VERSIONING_POLICY.md).

## Enterprise SaaS: честный вывод по текущему репозиторию

- **Нет модели «владелец платформы» (vendor tenant)** и потока self-service, при котором внешний бизнес регистрируется как новый клиент SaaS, а оператор платформы видит все организации в отдельном контуре. Есть **`Organization`** и **`Clinic.organization_id`**, но изоляция данных в коде и комментариях к entity опирается на **`clinic_id`**; провижининг «нового SaaS-клиента» как продукта **не выведен** в отдельный безопасный контур.
- Префикс API **`/owner/`** (`owner_omni_*`) **не** означает отдельный тип JWT или роль «владелец сети»: в `owner_omni_channels` используется **`get_current_admin`**, область — **`current_admin.clinic_id`** как `business_account_id`. Путаница с номенклатурой — **средний риск** для аудита и интеграций.
- **In-process EventBus** не заменяет межпроцессный/географически распределённый обмен событиями; горизонтальное масштабирование API требует отдельной стратегии (outbox, очередь, идемпотентность). Пример сквозной цепочки: [domains/booking_event_chain.md](./domains/booking_event_chain.md).
- **Поставка:** перечень активных GitHub Actions и отключённых workflow — в [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) и U-008; не путать «много тестов в `tests/`» с «CI гарантирует main».

## Как это работает в целом (логика по коду)

Один процесс **FastAPI** (`src/main.py`) монтирует единый `api_router` с префиксом `settings.api_v1_prefix` (часто `/api/v1`) и при отличии от `/api/v1` дублирует mount для совместимости. Запрос проходит CORS → middleware `X-Trace-Id` → middleware длительности Prometheus → обработчик роутера. Роутеры в `src/api/v1/routers/` получают **`AsyncSession` через `Depends(get_session)`** (`src/api/v1/dependencies.py` → `get_db` в `src/infrastructure/database/base.py`): после успешного запроса сессия **коммитится**, при исключении — **rollback**. Для админских прав используется **`require_permissions(...)`**, который строит **`RequestContext`** из JWT: для админа подгружаются роли и permissions через `RbacServiceImpl` + `RbacRepositoryImpl`. Бизнес-логика сосредоточена в **`src/application/services/`**: сервисы вызывают репозитории из `src/infrastructure/database/*_repo_impl.py` и/или прямой SQLAlchemy, публикуют события через **`get_event_bus().publish(...)`** (in-process `EventBus` в `src/application/events/event_bus.py`), обработчики регистрируются при старте в `lifespan`. Тяжёлая отложенная работа — **Celery** (`src/infrastructure/messaging/celery_app.py`), брокер и кэш — **Redis**. Фронт — **SPA React**: маршруты в `frontend/src/App.tsx`, HTTP только через **`API_BASE` `/api`** и Bearer из `localStorage` (`frontend/src/api/client.ts`), серверное состояние — **TanStack Query** с ключами из `queryKeys.ts`.

## Как читать

0. [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md) — **единый документ** для обзора архитектуры и сводной оценки SaaS; далее — модули по темам.
0b. [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) — **углубление:** транзакции vs события, платежи/webhook, БД, что делать с нуля.
0c. [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) — **приёмка:** вердикт, P0–P2, doc↔код, оси 1–14, красные флаги (см. рубрику).
0d. [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) — **целевая** модель platform / organization / clinic и полномочия super-owner.
0e. [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) — **наглядный план:** фазы, базовый пакет vs опции, отказ от box, vertical-agnostic, связка ADR/доков.
1. [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md) — правила точности и структуры секций.
2. [00_system_runtime.md](./00_system_runtime.md) — точка входа процесса, HTTP, compose, клиент SPA.
3. Backend по слоям:
   - [backend/api_layer.md](./backend/api_layer.md)
   - [backend/application_layer.md](./backend/application_layer.md)
   - [backend/domain_layer.md](./backend/domain_layer.md)
   - [backend/infrastructure_layer.md](./backend/infrastructure_layer.md)
   - [backend/core_crosscutting.md](./backend/core_crosscutting.md)
4. Frontend по зонам:
   - [frontend/routing_and_shells.md](./frontend/routing_and_shells.md)
   - [frontend/api_state.md](./frontend/api_state.md)
   - [frontend/admin_domain.md](./frontend/admin_domain.md)
   - [frontend/app_patient_domain.md](./frontend/app_patient_domain.md)
   - [frontend/shared_ui_and_pwa.md](./frontend/shared_ui_and_pwa.md)
5. [05_data_migrations_multitenancy.md](./05_data_migrations_multitenancy.md) — Alembic, схема, тенантность.
5b. [09_backup_restore_bcp.md](./09_backup_restore_bcp.md) — backup, BCP, связь с ADR-008 и [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md).
5c. [modules/data_migration_import_connectors.md](./modules/data_migration_import_connectors.md) — импорт из CRM/ERP (ADR-010).
5d. [modules/platform_subscription_billing.md](./modules/platform_subscription_billing.md) — webhook подписки платформы, провижининг (ADR-011), возврат/chargeback §12 (ADR-012).
5e. [ENTITLEMENT_ROUTER_INVENTORY.md](./ENTITLEMENT_ROUTER_INVENTORY.md) — инвентарь роутер ↔ entitlement (мастер-план §12.2).  
5f. [ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md](./ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md) — сводка ключей §4 / §16.5 / §24 (Phase 0).  
5g. [specs/OWNER_API_SEMANTICS_U005_DRAFT.md](./specs/OWNER_API_SEMANTICS_U005_DRAFT.md) — черновик U-005 `/owner/*`.  
5h. [specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](./specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md) — черновик Фазы 1a: `/platform/*` vs `/admin/*`.
6. [06_cache_redis_celery.md](./06_cache_redis_celery.md) — Redis, Celery, очереди.
7. [07_metrics_observability.md](./07_metrics_observability.md) — Prometheus, дашборды, алерты.
8. [08_tests_matrix.md](./08_tests_matrix.md) — pytest, e2e, фронтовые тесты.
9. [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) — оси зрелости Enterprise SaaS.
10. [domains/booking_event_chain.md](./domains/booking_event_chain.md) — пример домена: booking → события → подписчики.  
10b. [domains/commerce_bounded_context.md](./domains/commerce_bounded_context.md) — **Фаза 4 (опция):** магазин / продажи / 1С, ADR-013; **единый план + корпус `.md`:** [domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md](./domains/COMMERCE_STORE_ARCHITECTURE_PLAN.md).  
10c. [domains/staff_feed_wall_hardening.md](./domains/staff_feed_wall_hardening.md) — лента персонала на дашборде: вложения, инвалидация, e2e, виртуализация (план QA_ARCH/DEV).

**QA_ARCH gap scan (риски × рубрика × 8W):** [./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).  
**QA_ARCH масштаб Enterprise SaaS (@ARCH / @DEV, упущения и префлайт):** [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](./ENTERPRISE_SAAS_SCALE_ENVELOPE.md).  
**@QA_ARCH сквозное §27–§31 (антиспам, security-метрики, envelope ошибок, omni/SSE):** [arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) · статусы **10-Q***: [arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).
**QA_ARCH Phase 0 SaaS (D0):** [../artifacts/QA_REPORT_SaaS_P0_D0.md](../artifacts/QA_REPORT_SaaS_P0_D0.md).  
**Phase 0 @DEV — grep-аудит контуров A/B (webhook/платежи):** [../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](../artifacts/WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md).

Журнал неясностей: [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md).

## Статус фаз (заполнение документа)

| Фаза | Документ(ы) | Статус |
|------|-------------|--------|
| 0 | INDEX, CONVENTIONS, UNRESOLVED | принято |
| 1 | 00_system_runtime | принято (черновик по коду) |
| 2 | backend/*.md | принято (обзор по пакетам) |
| 3 | frontend/*.md | принято (обзор по зонам) |
| 4 | 05_data_migrations_multitenancy | принято |
| 5 | 06_cache_redis_celery | принято |
| 6 | 07_metrics_observability | принято |
| 7 | 08_tests_matrix | принято |
| QA | ENTERPRISE_SAAS_RUBRIC, Enterprise-аудит в каждом файле | принято (итерация 2026-04) |

Критерий «готово» для подсистемы: есть входы/выходы, якоря в файлах, таблица статуса (реализовано / частично / формально / неясно), при необходимости — ссылка в UNRESOLVED; для Enterprise — секции **Enterprise-аудит** и **Соответствие фактам**.

## Связанные материалы

- [../product_state/BACKEND_PASSPORT.md](../product_state/BACKEND_PASSPORT.md) — роутеры, конфиг.
- [../product_state/FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md) — маршруты SPA; пер-странично — [../frontend/pages/README.md](../frontend/pages/README.md).
- [../ARCH_AUDIT_NEXT.md](../ARCH_AUDIT_NEXT.md) — короткие отметки по волнам аудита.

### Enterprise-аудит (честная оценка) — каталог `docs/architecture/`

- **Критические риски:** отсутствие контура platform-operator и self-service onboarding нового бизнес-клиента при строгой изоляции тенантов; риск долгой эволюции схемы без явной стратегии RLS/организационного корня (см. рубрику, ось «Идентичность и границы тенанта»).
- **Средние риски:** номенклатура `/owner/*` vs фактический `AdminUser` + `clinic_id`; EventBus только внутри процесса API.
- **Формально / недоделано:** документы описывают «что есть в коде», но не заменяют penetration-тест, нагрузочное тестирование и аудит облака.
- **Рекомендуемые доработки:** проектный ADR на модель тенанта (platform / org / clinic), отдельный контур auth для оператора платформы или явное решение «single-tenant deploy only»; унификация имён API или введение отдельного guard для сетевого владельца, если продукт это требует; закрытие пунктов [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) с обновлением рубрики и MASTER.

### Соответствие фактам (проверка)

- Утверждения о `Organization`, `clinic_id`, `owner_omni_*` и `get_current_admin` проверены чтением `src/domain/entities/organization.py`, `clinic.py`, `src/api/v1/routers/owner_omni_channels.py`.
- Полный обход всех `*.py`/`*.tsx` на риски не выполнялся (см. границы в плане QA_ARCH).

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** несогласованность «документ vs код» при эволюции EventBus и webhook без обновления карты; см. [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md).
- **Что усилить:** держать INDEX как оглавление: при добавлении модульного файла — строка здесь и в [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md) §13.
- **С нуля:** отдельный индекс ADR в репо (вне текущего каталога) — по решению команды.
- **БД:** пробелы уровня схемы описывать в фундаментальном документе и U-*.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); операционный бэклог приёмки: [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).
