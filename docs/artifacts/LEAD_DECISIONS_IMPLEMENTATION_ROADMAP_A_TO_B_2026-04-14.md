# LEAD — план решений и реализация A→B по бизнес/логическим упущениям

Цель: перевести текущий контур из состояния **A (частично работающий, с ручными обходами и MVP-debt)**  
в состояние **B (детерминированный production-поток, с тестовыми и метриковыми гарантиями)**.

Связанный аудит: `docs/artifacts/QA_ARCH_BUSINESS_AND_LOGIC_GAPS_AUDIT_2026-04-14.md`.

---

## 0. Принятые решения (Decision Log)

### D1. Owner onboarding после оплаты должен быть полностью автоматическим

- Убираем зависимость от ручного mint/передачи токена.
- После provision запускаем транзакционную доставку приглашения (email как минимум, sms опционально).
- Добавляем пользовательский post-payment completion экран.

### D2. Checkout return URL должен быть под контролем платформы

- Запрещаем произвольные внешние `return_url` без allowlist.
- В production разрешаем только домены из конфигурации.

### D3. Критические тесты не имеют права «тихо скипаться»

- Вводим CI-гейт: для критического набора `skip == 0`, `error == 0`.
- Если инфраструктура недоступна, job падает, а не уходит в `skip`.

### D4. Для каждого критического потока вводим измеримый SLO/SLI

- Signup→Provision→InviteAccept покрывается метриками и алертами.

### D5. MVP-debt закрываем в risk-first порядке

- Сначала контуры выручки/доступа (owner signup, webhook security, tenant routing), затем функциональные хвосты.

---

## 1. Дорожная карта A→B (этапы)

## Этап A1 (Critical path hardening): owner signup real-time

**Статус (2026-04-14): реализовано в коде (MVP):** transactional outbox для письма с ссылкой `/signup/owner-invite?token=…`, цикл drain outbox в webhook B, публичный `GET /api/v1/public/platform/signup/intents/{id}/status` с полями **`next_action`** (стабильный enum для SPA) и **`next_step_hint`** (текст), страница фронта `ROUTE_PATHS.marketing.ownerInviteAccept`, метрики **`platform_owner_invite_email_total`**, **`platform_owner_invite_accept_total`**, гистограмма **`platform_signup_to_invite_delivery_seconds`**, алерты в `deploy/prometheus/dental_booking_alerts.yml` (серия `PlatformOwnerInvite*`). Дальше по дорожной карте: A2, A3.

### Scope

1. Реализовать автоматическую отправку owner invite:
   - producer: после `_provision_owner_invite`;
   - transport: Celery task + `EmailSender` (и fallback channel по политике);
   - шаблон: одноразовая ссылка на страницу accept invite.
2. Добавить public completion страницу/endpoint статуса:
   - статус intent (`pending_payment`, `paid`, `active`, `provision_failed`, `dead_letter`);
   - понятный next action.
3. Обработать edge-cases как first-class сценарии:
   - email занят;
   - email отсутствует;
   - token expired.

### Acceptance Criteria

- ≥ 99% успешных оплат доходят до состояния «invite delivered OR explicit user-facing failure reason».
- Нет ручного шага founder для стандартного happy-path.

### Тесты (обязательные)

- Unit:
  - генерация one-time invite URL;
  - корректная инвалидация старого токена;
  - идемпотентная отправка уведомления при повторном событии.
- API integration:
  - checkout → webhook succeeded → provision active → invite_accept;
  - email collision → детерминированный код ошибки + статус intent.
- Async integration:
  - Celery task отправки invite, retry policy, DLQ path.
- E2E:
  - marketing checkout flow до экрана завершения.

### Метрики/алерты

- Counters (как в коде):
  - отправка invite: **`platform_owner_invite_email_total{result=…}`** (`sent`, `deferred_send_failed`, `skipped_*`, …) — аналог желаемого `*_send_total`;
  - accept: **`platform_owner_invite_accept_total{result=ok|invalid_or_expired|password_too_short|rate_limited|server_error}`** — `invalid_or_expired` без разделения токен/срок (anti-enumeration).
- Latency: **`platform_signup_to_invite_delivery_seconds`** (histogram; observe при успешной отправке invite-email из outbox).
- Alerts: `PlatformOwnerInviteEmailHardFailures`, `PlatformOwnerInviteAcceptServerErrors`, `PlatformOwnerInviteAcceptRateLimitedBurst`, `PlatformOwnerInviteEmailConfigDeferredSustained`, `PlatformOwnerInviteAcceptInvalidBurst`; всплеск прочих `result` по email — Grafana по `platform_owner_invite_email_total`.

---

## Этап A2 (Security hardening): return_url + webhook governance

**Статус (2026-04-14):** политика `PLATFORM_CHECKOUT_RETURN_URL_ALLOWLIST` + API `return_url_not_allowed` и тесты — в коде. **Contour A в production:** пустой `PATIENT_PAYMENT_WEBHOOK_SECRET` уже даёт **fail-fast на старте** через `assert_required_security_secrets_in_production()` в `lifespan` (`src/main.py`), вместе с остальными обязательными секретами PRC-A3. Дополнительный флаг `ENFORCE_PATIENT_PAYMENT_WEBHOOK_SECRET_IN_PRODUCTION` — отдельная жёсткая политика только для контура A (см. `LEAD_PHASE0_GOVERNANCE_DECISIONS`). Метрики `platform_checkout_rejected_total` / `payment_webhook_governance_state` и алерты в `deploy/prometheus/dental_booking_alerts.yml` — реализованы. П.3 (founder mint): тест `test_platform_mint_owner_invite_logs_platform_audit` (`tests/api/test_platform_internal.py`) фиксирует вызов `log_platform_audit` при mint; ответ mint — **`Cache-Control: no-store`** (JSONResponse), чтобы токен не кэшировался прокси/браузером; UI-маскировка токена — по желанию продукта.

### Scope

1. `return_url` policy:
   - новая настройка `PLATFORM_CHECKOUT_RETURN_URL_ALLOWLIST`;
   - при несоответствии домену → 400 `return_url_not_allowed`.
2. Contour A webhook:
   - в production запрещаем пустой `PATIENT_PAYMENT_WEBHOOK_SECRET` (fail-fast).
3. Founder raw token handling:
   - endpoint mint оставляем только как break-glass;
   - сокращаем доступ, усиливаем аудит, опционально маскируем ответ в UI.

### Acceptance Criteria

- Нельзя инициировать checkout с произвольным внешним redirect.
- Production не стартует с insecure webhook governance.

### Тесты (обязательные)

- API tests:
  - allowlisted return_url проходит;
  - неразрешённый return_url блокируется.
- Config tests:
  - production config с пустым webhook secret → deterministic fail.
- Security tests:
  - founder mint endpoint audit log обязателен.

### Метрики/алерты

- `platform_checkout_rejected_total{reason=return_url_not_allowed}`.
- `payment_webhook_governance_state{contour=patient}` (gauge 0/1).

---

## Этап A3 (Test reliability): zero-skip policy для критических сценариев

**Статус (2026-04-14): реализовано (MVP CI gate):**
- маркер pytest `critical_path` (`pyproject.toml`);
- набор тестов: governance webhooks, platform outbox provision (основной сценарий invite-email), public checkout/status/allowlist, contour A webhook + idempotency, platform founder health, production defaults settings, e2e smoke `tests/e2e/test_critical_path_smoke.py` (vite preview + `/signup/owner-invite`; smoke после async API — reorder в `conftest`); тест `test_owner_invite_email_outbox_increments_attempts_when_smtp_missing` только в полном suite (нестабильный TRUNCATE/asyncpg на части окружений);
- `CRITICAL_PATH_CI=1` в conftest: недоступный Postgres/Redis для инфраструктурных сценариев → **fail**, не skip; то же для `redis_integration` при отключённом Redis;
- `scripts/ci/assert_pytest_junit_xml_gate.py` — проверка JUnit: `skipped=errors=failures=0`, `passed>0`;
- workflow **`.github/workflows/critical-path-gate.yml`** (Postgres + Redis + build + preview + `pytest -m critical_path --strict-markers` + gate).

Локально: `FRONTEND_E2E_URL=http://127.0.0.1:4173` + preview; для строгого режима как в CI — `CRITICAL_PATH_CI=1`.

### Scope

1. Выделить `pytest -m critical_path` набор:
   - signup/provision/invite;
   - webhook verification;
   - founder auth критические маршруты.
2. В CI для этого набора:
   - поднять Postgres/Redis/frontend preview всегда;
   - запуск с отчётом skip/error;
   - fail build если `skipped > 0` или `errors > 0`.
3. Нормализовать `tests/conftest.py`:
   - для critical profile запрещаем skip по infra (ошибка вместо skip);
   - явная preflight-проверка инфраструктуры.

### Acceptance Criteria

- Для critical profile: `passed > 0`, `skipped = 0`, `errors = 0`.
- Повторяемость прогона между локально и CI (Linux baseline).

### Тесты (обязательные)

- Self-test CI job:
  - парсинг `pytest --json-report` / `junitxml` и проверка `skip==0`.
- Smoke script:
  - preflight readiness db/redis/frontend.

### Метрики/алерты

- `ci_critical_tests_skipped_total`.
- `ci_critical_tests_failed_total`.
- Alert в CI notifications при `skipped > 0`.

---

## Этап B1 (High debt closure): multi-tenant routing и интеграции

**Статус (2026-04-14): частично в коде (MVP):** `resolve_business_account_for_integration_webhook` (`integration_route_resolution.py`), явный `omni_channels.id` через `POST .../integrations/webhooks/{telegram|whatsapp|vk|instagram|email}/channels/{channel_id}` и `integration_channel_id` / query `integration_channel_id` для webchat; при нескольких клиниках без channel — `400 integration_route_required` если `INTEGRATION_GATEWAY_LEGACY_FIRST_CLINIC_FALLBACK=false`, иначе первая клиника по `clinics.id` (deprecated). Метрика `integration_route_resolution_total{result}`. Интеграционные тесты: **два org / два канала** — `test_telegram_two_orgs_channel_routes_to_correct_clinic`; **одна org / две клиники / два канала** — `test_telegram_same_org_two_clinics_channels_resolve_separately`. Дальше: org-level секреты/провайдер metadata, оставшиеся stub-зоны.

### Scope

1. Убрать first-clinic routing в `integrations_gateway.py`.
2. Ввести детерминированное сопоставление tenant по секрету/каналу/provider metadata.
3. Закрыть ключевые `stub` зоны, где обещана production готовность.

### Acceptance Criteria

- Входящие события провайдера всегда маршрутизируются в правильную клинику/организацию.

### Тесты

- Integration tests на 2+ клиники одного org + 2 org.
- Negative tests на неверный/отсутствующий route key.

### Метрики

- `integration_route_resolution_total{result=matched|singleton|legacy_fallback|ambiguous|not_found|type_mismatch}`.

---

## Этап B2 (Medium debt): финансы, loyalty, compliance lifecycle

**Статус (2026-04-14):** п.1 частично — `ErpVisitServiceItem.total_amount` и платёжные строки в `BookingCompletionService` согласованы с базой выручки `BookingErpService` (предоплата vs кошелёк); `ErpVisitPaymentItem.source` маппится с `payments.provider` (`acquiring`/`cash`/`deposit`/`other`), подписка без карточного платежа — `package`. Юнит-тесты: `tests/services/test_booking_completion_ledger_helpers.py`. **Loyalty intent (запись):** суффикс в `booking.notes` + `use_subscription_id` в patient create + стрип в `BookingRead` (`booking_loyalty_intent`, `tests/application/test_booking_loyalty_intent.py`, UI query на `BookingWizardPage`). **Compliance:** `POST /api/v1/patients/{id}/anonymize`, метрика `patient_pii_anonymized_total`, запись в **`rbac_audit_log`** (`action=patient_pii_anonymized`), для `patients.deleted_at` — naive UTC (`utc_now_naive`), тесты `tests/api/test_patients_anonymize.py`; soft-delete в репозитории выровнен на naive UTC; операторская заметка — `docs/operations/PII_LOGGING.md`. Дальше: loyalty family / полный delete-policy / reconciliation.

### Scope

1. `booking_completion_service` — закрыть TODO по источникам оплат и скидкам.
2. Loyalty family scenarios — довести редиректы и политику.
3. Patient data lifecycle — добавить анонимизацию/удаление по policy.

### Acceptance Criteria

- Отчёты не расходятся с первичными финансовыми событиями.
- Для пациентских данных есть формализованный и тестируемый delete/anonymize flow.

### Тесты/метрики

- Финансовые reconciliation tests + метрика расхождения.
- Compliance flow tests + audit events.

---

## 2. План реализации по спринтам (предложение)

1. Спринт 1: A1.
2. Спринт 2: A2 + A3.
3. Спринт 3: B1.
4. Спринт 4: B2.

Правило выпуска: без выполнения A1+A2+A3 релиз в production не рекомендован.

---

## 3. Изменения в CI/CD (обязательно)

1. ~~Добавить отдельный workflow/job `critical-path-gate`.~~ **Сделано:** `.github/workflows/critical-path-gate.yml`.
2. Job должен:
   - поднять infra сервисы;
   - выполнить migrations (через session `init_db` в pytest);
   - прогнать `pytest -m critical_path` и e2e signup smoke;
   - проверить отчёт: `skip=0`, `error=0` (`assert_pytest_junit_xml_gate.py`).
3. Если условия не выполнены — merge block (workflow exit ≠ 0).

---

## 4. Определение «готово» (Definition of Done)

Задача по каждому пункту считается закрытой только если одновременно выполнено:

1. Реализация в коде + документация в `.env.example` и runbook.
2. Автотесты добавлены и проходят в CI.
3. Для critical задач нет skip/error в соответствующем test profile.
4. Метрики публикуются в `/metrics`, для критичных есть alert rule.
5. Есть операционный сценарий обработки ошибок (runbook).

---

## 5. Риски внедрения и контрмеры

- Риск: усложнение onboarding UX.  
  Контрмера: staged rollout + feature flag + product copy sync.
- Риск: ложные срабатывания anti-skip gate.  
  Контрмера: отдельный стабильный CI profile и preflight readiness checks.
- Риск: утечки invite token в ручных операциях.  
  Контрмера: минимизация break-glass endpoint usage + audit + TTL + rotation.

---

*Документ LEAD. Обновлять при изменении приоритетов, CI gate или SLO для критических потоков.*
