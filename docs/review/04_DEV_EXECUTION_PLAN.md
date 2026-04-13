# DEV Execution Plan (Executable, Non-Formal, Production Grade)

Цель: закрыть все текущие `PARTIAL` зоны до состояния "реально готово к live", без "формально закрыто". See ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md for UI acceptance. См. также [ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) для приёмки UI.

## Правила исполнения @DEV (updated)

1. Каждая задача фазы закрывается только при наличии:
   - кода,
   - автотестов (позитив + негатив),
   - операционного доказательства (runbook/checklist/алерт),
   - синхронизации статуса в `docs/architecture/arch_plan/STREAM_PRODUCTION_READINESS.md`.
2. Нельзя закрыть фазу "по документу" без проверки фактического runtime-поведения.
3. Любой временный компромисс оформляется как risk/waiver с владельцем и датой пересмотра.

## Архитектурные ограничения (фиксированы заранее)

1. Контур `A` (patient payments) и контур `B` (platform billing) не смешивать ни по секретам, ни по обработчикам.
2. Для публичных денежных путей при `replicas(API) >= 2` обязательно соблюдение решения из `§17.1` (outbox/ограничение/ADR риска).
3. Entitlement enforcement не заменяется UI-скрытием; серверные проверки обязательны.
4. Метрики и алерты должны оставаться low-cardinality в critical path.
5. Любая доработка P0 не должна ломать существующие контракты API без явной версии/миграции.

## Порядок реализации (dependency order)

Работать строго в таком порядке:

1. `Phase 1` (security baseline)
2. `Phase 2` (money-flow reliability)
3. `Phase 3` (entitlements correctness)
4. `Phase 4` (observability/incident readiness)
5. `Phase 5` (CI hardening)

Переход в следующую фазу запрещён, если не выполнены критерии выхода текущей.

## Формат рабочего среза (обязательный шаблон)

Каждый срез @DEV оформляет в одном PR:

- **Scope:** 1 capability (максимум 2 связанных).
- **Code:** список изменённых файлов.
- **Tests:** список добавленных/обновлённых тестов.
- **Ops evidence:** какой runbook/checklist/alert обновлён.
- **PRC sync:** какие строки `PRC-*` меняются и почему.
- **Risk note:** что осталось вне среза (если есть).

## Phase 1 — Security and Identity Hardening (P0)

### Задачи

1. Секреты в production:
   - закрепить fail-closed для критичных секретов в production режиме;
   - исключить режим "работаем в проде без platform/patient webhook секретов";
   - унифицировать загрузку секретов через runtime provider.
   - ключевые области: `src/core/runtime_secrets.py`, `src/core/config.py`, `src/core/payment_webhook_governance.py`, `src/main.py`.

   **Минимальный перечень критичных секретов (обязателен для fail-closed):**
   - `PATIENT_PAYMENT_WEBHOOK_SECRET`
   - `PLATFORM_BILLING_WEBHOOK_SECRET`
   - `PLATFORM_FOUNDER_JWT_SECRET` (или эквивалентный runtime-secret ключ)
   - `JWT_SECRET_KEY` (если используется в прод-контуре tenant auth)

   **Жёсткое правило:** если `APP_ENV=production` и любой из обязательных секретов пуст/не загружен, приложение не стартует.

2. Founder access hardening:
   - зафиксировать и покрыть тестами обязательность founder 2FA для production;
   - проверить и усилить сценарии break-glass (потеря 2FA, восстановление, аудит).
   - ключевые области: `src/api/v1/routers/platform_founder_auth.py`, `src/api/v1/routers/platform_internal.py`, `docs/operations/FOUNDER_ACCESS_BREAKGLASS.md`.

3. Public-edge abuse closure:
   - подтвердить rate-limit/captcha на всех чувствительных публичных путях (signup, webhook B, embed, auth-sensitive);
   - добавить недостающие негативные тесты.
   - ключевые области: `src/api/v1/routers/platform_billing.py`, `src/api/v1/routers/public_platform_signup.py`, `src/api/v1/routers/public_embed.py`, `tests/api/test_platform_billing.py`.

### Рабочие пакеты (WP)

- **WP1.1 Secret fail-closed bootstrap**
  - Реализовать fail-closed поведение для production на отсутствие критичных секретов.
  - Проверить и согласовать поведение локальной/тестовой среды.
  - Минимальные тесты:
    - старт production без секрета -> ожидаемый отказ старта;
    - старт test/local без mandatory prod secrets -> разрешён по политике.
  - Артефакты закрытия:
    - unit/integration тесты на fail-closed,
    - обновлённый фрагмент в `docs/operations/RELEASE_CHECKLIST.md` (проверка secret loading),
    - ссылка в `STREAM_PRODUCTION_READINESS.md` на конкретный PR/отчёт.

- **WP1.2 Founder 2FA enforcement**
  - Проверить, что founder critical endpoints недоступны без TOTP в production policy.
  - Закрыть edge cases для re-enroll/recovery.
  - Минимальные тесты:
    - founder login без enroll при required policy -> отказ;
    - founder with valid TOTP -> доступ;
    - recovery path audit trail фиксируется.
  - Артефакты закрытия:
    - тесты API на ветки allowed/forbidden для founder auth,
    - обновлённый `docs/operations/FOUNDER_ACCESS_BREAKGLASS.md` (шаги и аудит),
    - синхронизация `PRC-A3` при выполнении условий.

- **WP1.3 Public anti-abuse completeness**
  - Свести матрицу чувствительных публичных путей и защиты (rate-limit/captcha/waf expectations).
  - Добавить недостающие ограничения/метрики.
  - Минимальные тесты:
    - webhook burst -> 429/ограничение;
    - signup abuse path -> ограничение;
    - embed abuse path -> ограничение.
  - Артефакты закрытия:
    - таблица "путь -> защита -> тест" в PR description или артефакте,
    - подтверждение метрик/алертов (rate-limited события видны в мониторинге),
    - синхронизация `PRC-C1`/`PRC-B7` по факту.

### Критерии выхода из фазы

- `PRC-A3` и security-часть `PRC-C1` переводятся в `satisfied` с артефактами.
- Нет запуска production при пустых критичных секретах.
- Негативные тесты на bypass/abuse проходят в CI.
- В `RELEASE_CHECKLIST` есть явная проверка secret-policy и anti-abuse policy.
- Зафиксированы и проверены startup-ветки: `production` (fail-closed) и `test/local` (policy-based allow).

## Phase 2 — Money Flow Reliability Closure (P0)
### Задачи

### Задачи

1. Retry/DLQ/reconcile довести до операционной готовности:
   - завершить state-machine для stuck/failed provisioning;
   - обеспечить идемпотентный force-retry без повторного списания;
   - закрыть ручной reconcile founder UI/API end-to-end.
   - ключевые области: `src/application/services/platform_billing_service.py`, `src/api/v1/routers/platform_internal.py`, `frontend/src` (founder/provision queue UI), `tests/api/test_platform_billing.py`.

2. Outbox + replicas safety:
   - подтвердить целостность при `replicas >= 2`;
   - обеспечить deterministic dispatch/recovery при падении воркера/API;
   - выполнить проверку redelivery/stuck-case.
   - ключевые области: `src/application/services/domain_outbox_service.py`, `src/infrastructure/messaging/tasks/domain_outbox_tasks.py`, `tests/application/test_domain_outbox_platform_provision.py`.

3. Refund/chargeback code closure по ADR-012:
   - довести кодовую реализацию отзыва entitlements и terminal states;
   - покрыть тестами сценарии refund/chargeback.

### Рабочие пакеты (WP)

- **WP2.1 Provision retry/DLQ state machine**
  - Финализировать состояния `stuck/failed/recoverable/terminal`.
  - Исключить повторные необратимые side effects при force-retry.
  - Тесты:
    - repeated webhook + retry не создаёт дублей;
    - переход в DLQ и последующий ручной recover;
    - permanent failure корректно помечается и алертится.

- **WP2.2 Reconcile UI/API founder flow**
  - Убедиться, что founder может завершить операционный цикл без ручного SQL.
  - UI/UX: actionable queue, статус, retry action, audit trace.
  - Тесты:
    - end-to-end stuck -> reconcile -> success;
    - forbidden/invalid actions correctly blocked.

- **WP2.3 Outbox/replica deterministic behavior**
  - Подтвердить deterministic dispatch при падениях воркеров и restart.
  - Документировать фактический режим для replicas.
  - Тесты:
    - post-commit dispatch failure -> eventual recover via task;
    - redelivery не ломает идемпотентность.

- **WP2.4 ADR-012 code closure**
  - Реализовать refund/chargeback lifecycle до terminal consistency.
  - Тесты:
    - refund -> revoke entitlements (идемпотентно);
    - chargeback -> статус и ограничения доступа корректны;
    - повторное событие refund/chargeback не дублирует side effects.

### Критерии выхода из фазы

- `PRC-B4`, `PRC-B5`, `PRC-E1`, `PRC-E3` переведены в `satisfied`.
- Есть runbook-пруф на восстановление после провала post-payment provisioning.
- Нет сценария "деньги приняты, доступ не восстановим операционно".
- Для ключевых failure-path есть алерты с `runbook_url`.

## Phase 3 — Entitlements and Migration Correctness (P1)

### Задачи

1. Legacy-enforcement ambiguity:
   - ввести управляемый rollout/backfill для `organization_entitlements`;
   - документировать и реализовать явные режимы для legacy и новых org.
   - ключевые области: `src/application/services/organization_entitlement_access.py`, миграции Alembic, `docs/architecture/ENTITLEMENT_ROUTER_INVENTORY.md`.

2. Hard regression tests:
   - добавить тесты на bypass entitlement при edge-conditions;
   - проверить несоответствие UI-nav и backend-gate.

3. Консистентность API/UI:
   - проверить, что скрытие в UI не подменяет серверный запрет.

### Рабочие пакеты (WP)

- **WP3.1 Legacy rollout/backfill plan**
  - Ввести явный migration/backfill механизм для legacy org.
  - Зафиксировать policy: какие org и когда переходят на strict enforcement.

- **WP3.2 Bypass regression suite**
  - Добавить негативные тесты для edge-cases, где возможен обход entitlement.
  - Покрыть API и critical router-level checks.

- **WP3.3 UI/API parity verification**
  - Проверить соответствие навигации и backend restrictions.
  - Добавить проверку, что "скрыто в UI" != "разрешено на API".

### Критерии выхода из фазы

- `PRC-D1`, `PRC-D2` остаются `satisfied` после новых тестов.
- Нет legacy-организаций с "неявно всё открыто" без бизнес-решения.
- Есть миграционный отчёт по cohort-переходу legacy -> enforced.

## Phase 4 — Observability and Incident Readiness (P1)

### Задачи

1. Качество алертов:
   - severity, dedup/grouping, runbook_url для критичных правил;
   - владельцы и канал эскалации.
   - ключевые области: `deploy/prometheus/dental_booking_alerts.yml`, `docs/operations/RELEASE_CHECKLIST.md`, `docs/operations/SLO_CRITICAL_PATHS.md`.

2. Cardinality and SLO proof:
   - staging-пруф по low-cardinality метрикам;
   - доказать отсутствие high-cardinality labels в security/billing алертах.

3. Incident triage UX:
   - дашборды и метрики должны позволять локализовать инцидент без ручного "grep в проде".

### Рабочие пакеты (WP)

- **WP4.1 Alert policy normalization**
  - Унифицировать severity/grouping/dedup/runbook_url для P0/P1 алертов.
  - Закрыть пробелы для billing/outbox/security.

- **WP4.2 Cardinality proof**
  - Прогон staging checks по новым/критичным метрикам.
  - Подтвердить отсутствие high-cardinality leakage.

- **WP4.3 Incident runbook fitness**
  - Проверить, что из алерта можно прийти к точному runbook-шагу и восстановлению.
  - Обновить OPS smoke checklist.

### Критерии выхода из фазы

- `PRC-F1`, `PRC-F2`, `PRC-F3`, `PRC-G2` переведены в `satisfied`.
- Есть подтверждённый OPS smoke для observability.
- Все критичные алерты имеют owner и runbook reference.

## Phase 5 — CI and Release Gate Hardening (P1)

### Задачи

1. Укрепить PR-level quality gates:
   - обязательные тестовые сеты для критичных доменов (billing/provision/outbox/entitlements/security).
   - минимальный must-pass на каждый PR, затрагивающий P0 домены.

2. Снизить поверхность disabled workflows:
   - либо включить, либо явно заwaive-ить с датой и владельцем.

3. Стабилизировать release gate:
   - запрет релиза при незакрытых P0 PRC строках без waiver.

### Рабочие пакеты (WP)

- **WP5.1 Critical PR suite**
  - Ввести обязательный набор тестов на PR при изменениях в P0 доменах.
  - Зафиксировать mapping: домен -> обязательные test targets.

- **WP5.2 Workflow debt reduction**
  - Разобрать disabled workflows: enable/remove/waive с датой.
  - Не оставлять "молчаливо disabled" для критичных проверок.

- **WP5.3 Release guardrails**
  - Проверка PRC P0 статусов как обязательное условие release gate.
  - Явный отказ релиза при нарушении.

### Критерии выхода из фазы

- `PRC-E4` сохраняется `satisfied`, риски disabled-workflows снижены.
- Нет merge в релизный поток без прохождения критичных доменных тестов.
- Есть документированный policy "critical changes require critical suite".

## Delivery cadence (как исполнять)

1. Работать вертикальными срезами: код -> тесты -> операционное доказательство -> статус PRC.
2. Каждый срез не больше 1-2 рисковых capabilities одновременно.
3. После каждого среза обновлять:
   - `docs/review/03_CODE_REALITY_REVIEW.md` (факт прогресса),
   - `docs/architecture/arch_plan/STREAM_PRODUCTION_READINESS.md` (официальный статус),
   - при необходимости `docs/review/02_DOCUMENTATION_REVIEW.md` (если найдено новое расхождение).

## Test execution baseline (обязательный для @DEV)

Для backend test-pack использовать окружение Poetry, иначе возможны ложные падения по зависимостям:

- `poetry run pytest tests/core/test_payment_webhook_governance.py -q`
- `poetry run pytest tests/api/test_platform_internal.py -q`
- `poetry run pytest tests/api/test_phase1e_embed.py -q`
- `poetry run pytest tests/api/test_platform_billing.py -q`
- `poetry run pytest tests/application/test_domain_outbox_platform_provision.py -q` (Phase 2 / outbox B)
- `poetry run pytest tests/application/test_organization_entitlement_access.py -q` (Phase 3 / entitlement rollout)

Если запуск вне Poetry (`python -m pytest` системного Python), результат не принимается как доказательство закрытия capability.

## Definition of done для каждой capability

Capability считается закрытой только если одновременно:

1. Реализован основной поток.
2. Реализованы и протестированы негативные ветки.
3. Есть операционная процедура восстановления.
4. Метрики/алерты дают наблюдаемость инцидента.
5. PRC-статус обновлён на основании артефактов.

## Definition of completion

План завершён только когда:

1. Все критичные `PARTIAL` из `docs/review/03_CODE_REALITY_REVIEW.md` перешли в `DONE`.
2. В `STREAM_PRODUCTION_READINESS.md` отсутствуют незакрытые P0 строки без waiver.
3. Есть доказательства в коде, тестах и operations-артефактах, а не только в тексте.

## Остаточное закрытие PRC (среда и OPS, не только код)

Следующие строки матрицы зависят от **production/staging** или явной политики команды; в репозитории зафиксированы чеклисты и связи тест→путь:

| Тема | Артефакт |
|------|----------|
| **PRC-A3** — ASM в prod + OPS-тикет | [docs/operations/PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md](../operations/PLATFORM_AND_TENANT_SECRETS_RUNBOOK.md) § «Закрытие PRC-A3» |
| **PRC-C1 / B7 / F1 / F3 / G2** — staging-доказательства | [docs/operations/PRC_STAGING_EVIDENCE_CHECKLIST.md](../operations/PRC_STAGING_EVIDENCE_CHECKLIST.md) |
| Матрица публичных лимитов (WP1.3) | [docs/review/PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md](./PUBLIC_PERIMETER_RATE_LIMIT_MATRIX.md) |
| **WP5.2** — disabled workflows | [docs/architecture/arch_plan/CI_WORKFLOWS_WAIVERS.md](../architecture/arch_plan/CI_WORKFLOWS_WAIVERS.md) |

Релизный чеклист ссылается на эти документы: [docs/operations/RELEASE_CHECKLIST.md](../operations/RELEASE_CHECKLIST.md).
