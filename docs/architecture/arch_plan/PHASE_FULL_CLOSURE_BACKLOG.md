# Бэклог полного закрытия фаз (QA_ARCH / @ARCH)

> **Назначение:** единая матрица **долга сверх минимального DoD** фаз `arch_plan/`: что нужно, чтобы формулировать «фаза закрыта **полностью** по целевому образу МП», а не только по строкам DoD в `01_`…`10_`.  
> **Не дублирует** мастер-план: каждая строка **ссылается** на уже существующий якорь в [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) (**МП**), ADR или фазовом файле.  
> **Исполнение:** пункты закрываются **эпик-срезами** ([LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md)); при закрытии среза обновляйте колонку **Статус**.

| Колонка | Смысл |
|---------|--------|
| **ID** | Стабильный идентификатор долга (не менять при переименовании тикета). |
| **Статус** | `open` \| `in_progress` \| `done` \| `wontfix` (с краткой причиной). |
| **Источник** | Где требование уже зафиксировано (МП §, ADR, фаза). |

---

## Фаза 0 (Docs / Phase_0_Docs)

| ID | Что доделать до «полного» 0 | Источник | Статус | Примечание |
|----|-----------------------------|----------|--------|------------|
| 0-F1 | Envelope масштаба (N org, RPS, рост данных) — если заявляется Enterprise-честность | МП **§31**, [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) | **draft** | Черновик: [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md); **код-якоря:** `src/core/enterprise_scale_envelope.py`; утверждение чисел и PRC-G1 — **LEAD** |
| 0-F2 | Crash-review МП + TARGET + RUBRIC по процессу Phase 0 | [01_PHASE_0_PREPARATION.md](./01_PHASE_0_PREPARATION.md) @ARCH | **done** (2026-04-06) | **Решение LEAD:** [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md) §0-F2 + инженерный минимум: `phase0_governance_preflight.py`, [STREAM_PHASE0_AND_GOVERNANCE.md](./STREAM_PHASE0_AND_GOVERNANCE.md) |
| 0-F3 | Синхронизация INDEX / TARGET / RUBRIC | [STREAM_PHASE0_AND_GOVERNANCE.md](./STREAM_PHASE0_AND_GOVERNANCE.md) | **done** (2026-04-06) | Таблица **§2b** в [ENTERPRISE_SAAS_TARGET.md](../ENTERPRISE_SAAS_TARGET.md); LEAD: [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md) §0-F3 |
| 0-Q1 | Обязательный shared-secret или эквивалент SEC для **контура A** в prod при приёме платежей | U-006, [STREAM_PHASE0_AND_GOVERNANCE.md](./STREAM_PHASE0_AND_GOVERNANCE.md) | **done** (2026-04-06) | Дефолт: warning; жёсткий режим: `ENFORCE_PATIENT_PAYMENT_WEBHOOK_SECRET_IN_PRODUCTION` — [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md) §0-Q1 |
| 0-Q2 | Per-IP (и при необходимости edge) rate limit для `POST /api/v1/payments/webhook` | Симметрия с контуром B, §10 | **done** (2026-04-06) | `RATE_PATIENT_PAYMENT_WEBHOOK_*`, [payments.py](../../../src/api/v1/routers/payments.py) |
| 0-Q3 | Алерт по `payment_webhook_failures_total` (burst `invalid_secret`) | M-A1 [METRICS_REGISTRY.md](../../artifacts/METRICS_REGISTRY.md) | **done** (2026-04-06) | `PatientPaymentWebhookInvalidSecretBurst` в `deploy/prometheus/dental_booking_alerts.yml` |

*Дополняйте строками по итогам QA_ARCH циклов Phase 0.*

---

## Фаза 1a (Platform Core) — долг сверх DoD минимума

**Контекст:** минимальный DoD **1a** и вердикт @QA_ARCH «spine закрыт» — [02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md), [STREAM_1A_PLATFORM_EPICS.md](./STREAM_1A_PLATFORM_EPICS.md).  
Ниже — то, без чего **нельзя** называть 1a «полной» по **целевому образу** того же файла (п.1–2, 5–6) и МП **§16.1** (модель Основателя, 2FA, platform-таблицы / RLS fork).

| ID | Что доделать | Источник (уже в плане) | Статус | Эпик-срез (рабочее имя) |
|----|--------------|------------------------|--------|-------------------------|
| 1a-F1 | Учётная запись / сущность platform-operator в БД, выдача сессии или access token после аутентификации (не ручной mint JWT) | МП **§7–§9**, [ADR-007](../../adr/ADR-007-platform-multitenancy-super-admin.md), [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), [specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md](../specs/PLATFORM_ADMIN_API_BOUNDARY_DRAFT.md) «следующие шаги» | **done** (2026-04-06) | Срез **1a-E2:** `platform_founder_users`, миграция `20260422_platform_founder_users`, `platform_founder_auth`, `get_current_platform_founder`; [QA_REPORT_1a_E2](../../artifacts/QA_REPORT_1a_E2_platform_user.md), [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md). Mint в pytest — не продуктовый путь. |
| 1a-F2 | 2FA/TOTP для Основателя + политика bootstrap (согласованно с break-glass) | МП **§9**, **§19** п.10, [FOUNDER_ACCESS_BREAKGLASS.md](../../operations/FOUNDER_ACCESS_BREAKGLASS.md), [02_PHASE_1A](./02_PHASE_1A_PLATFORM_CORE.md) п.6 | **done** (2026-04-06) | Срез **1a-E3:** [QA_REPORT_1a_E3_founder_2fa](../../artifacts/QA_REPORT_1a_E3_founder_2fa.md) |
| 1a-F3 | Audit platform-уровня на чувствительных `/platform/*` (кто/когда/что; без PII в лишних полях) | [ADR-007](../../adr/ADR-007-platform-multitenancy-super-admin.md), МП **§1** / C5 | **done** (2026-04-06) | Срез **1a-E4:** structured `platform_audit`; [QA_REPORT_1a_E4_platform_audit](../../artifacts/QA_REPORT_1a_E4_platform_audit.md) |
| 1a-F4 | Ужесточение идентичности JWT: `iss`/`aud` или отдельный issuer; согласование с §19 п.3 | МП **§19** п.3, ADR-007 | **done** (2026-04-06) | Срез **1a-E6:** `src/core/security.py`, `JWT_*` / `jwt_*` settings, метрика `platform_founder_jwt_reject_total`; [QA_REPORT_1a_E6_jwt_hardening](../../artifacts/QA_REPORT_1a_E6_jwt_hardening.md); dual-read `JWT_LEGACY_ALLOW_MISSING_ISS_AUD` |
| 1a-F5 | **Опционально:** трек **A** изоляции (PostgreSQL RLS) вместо только application-layer + негативных тестов | [ADR-007](../../adr/ADR-007-platform-multitenancy-super-admin.md) fork; [02_PHASE_1A](./02_PHASE_1A_PLATFORM_CORE.md) п.3 | **done** (2026-04-06, GUC на `organization_entitlements`) | Срез **1a-E5:** [QA_REPORT_1a_E5_rls](../../artifacts/QA_REPORT_1a_E5_rls.md); полный RLS по всем tenant-таблицам — вне среза |

**Где это уже зафиксировано в корпусе (не дублируем смысл):** МП **§2b** и блок честности «Факт кода…» (platform-operator, RLS fork, platform-audit vs ADR-007), [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](../ARCHITECTURE_SAAS_MASTER_OVERVIEW.md); [LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md](../LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md) — «следующие эпик-срезы **1a+**».

---

## Фаза 1b (Commerce & UX)

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 1b-F1 | Полный провижининг §6 (первый Владелец, entitlements, не только Org+Clinic) | МП **§6**, **§2d** п.8, [03_PHASE_1B](./03_PHASE_1B_COMMERCE_AND_UX.md), ADR-011 | **done** (2026-04-06) | Срез **1b-E2** + [QA_REPORT_1b_E2_provision.md](../../artifacts/QA_REPORT_1b_E2_provision.md); лендинг/checkout (**1b-F5**) — отдельно |
| 1b-F2 | OpenAPI контура B, ветки провайдера, retry/DLQ/reconcile UI | МП **§16.6**, DoD **§15b 1b** | **done** (2026-04-07) | [QA_REPORT_1b_E3b_webhook_contract.md](../../artifacts/QA_REPORT_1b_E3b_webhook_contract.md), YAML [platform_yookassa_webhook_b_branches.yaml](../contracts/platform_yookassa_webhook_b_branches.yaml); pytest `tests/api/test_platform_billing.py` |
| 1b-F3 | Лендинг / signup / privacy / антиспам по воротам | МП **§5–§6**, **§19**, [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) | **in_progress** (2026-04-07) | Бэкенд: лимиты checkout/catalog/webhook B, TTL+expire job, метрика M-B9, тесты; приёмка: [STREAM_CROSS_CUTTING_GO_LIVE.md](./STREAM_CROSS_CUTTING_GO_LIVE.md). Хвост: капча на checkout, интеграционные Redis-тесты (**10-Q8**), UI лендинга/Product |
| 1b-F4 | **Планы-подписки:** цены пресета помесячно/на год; публичный каталог; `tariff_snapshot` + гейт суммы в webhook при `billing_period` | [03_PHASE_1B](./03_PHASE_1B_COMMERCE_AND_UX.md) п.8, [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 | **done** (2026-04-06) | Срез **1b-E1** + checkout; [QA_REPORT_1b_E1_checkout](../../artifacts/QA_REPORT_1b_E1_checkout.md) |
| 1b-F5 | **Публичный checkout:** создание `platform_signup_intent` из лендинга с `plan_slug` + **`billing_period`** + инициация платежа YooKassa на сумму из каталога; UI выбора «месяц / год» и CTA | МП **§6**, **§3** п.3, [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 | **done** (2026-04-06) | `POST /public/platform/signup/checkout`, лендинг `App.tsx`; отчёт **1b-E1** |
| 1b-F6 | **Согласованность гейта и retry:** `POST .../retry-provision` не должен обходить проверку «сумма провайдера vs каталог» без явного решения: повторный вызов гейта в `execute_platform_provision` **или** флаг «override» у Основателя + запись в audit (§25) | [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 бэклог | **done** (ядро, 2026-04-07) | Гейт в `execute_platform_provision` + `provision_blocked:*` без бессмысленного Celery backoff; см. `tests/api/test_platform_billing.py` |
| 1b-F6a | **Override гейта каталога** у Основателя с audit в БД (§25) — если Product разрешит обход при расхождении суммы | [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 | open | Явный API + immutable audit; не путать с reconcile «Retry» |
| 1b-F10 | **Grafana:** панели контура B (stuck/DLQ) и сверка с алертами Prometheus | [07_metrics_observability.md](../07_metrics_observability.md), `deploy/grafana` | **done** (2026-04-07) | Ряд в `dental_booking_observability_w1_w2.json`; tune порогов — OPS |
| 1b-F11 | **METRICS_PROTOCOL:** карточки M-B1…M-B8 (или свёртка) для контура B | [METRICS_REGISTRY.md](../../artifacts/METRICS_REGISTRY.md), `METRICS_PROTOCOL.md` | open | Реестр заведён; карточки — @PRINCIPLE / G4 |
| 1b-F12 | **Multi-replica:** webhook B и провижининг — outbox / sticky / запрет по [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) §17.1 | МП §19, ADR-009 | **partial** (2026-04-13) | Код: outbox-провижининг B (**2-F7**). **Хвост:** OPS-подтверждение ingress при 2+ репликах до прод-трафика |
| 1b-F7 | **Immutable audit в БД** по изменениям `platform_catalog_plans` (кто/когда/diff), не только structured log `platform_catalog_plan_upsert` | МП **§25**, строка **1a-F3** выше в этом файле, §4.3 | open | Можно объединить с платформенным audit-эпиком **1a-F3** одним PR |
| 1b-F8 | **Recurring / НДС / чек** по подписке платформы; скидка «год vs 12×месяц» в продуктовой политике | [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 open questions | open | Эпик Product + SEC + провайдер; не блокирует MVP каталога |
| 1b-F9 | **Internal CRUD опций** `platform_catalog_options` (симметрия с `PUT .../catalog/plans`); без этого «конструктор» только через миграции/сиды | МП **§3**, **§8**, [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3 | open | Эпик после стабилизации пресетов; валидация планов уже зависит от строк опций |

*Расширяйте таблицу по мере приёмки QA_ARCH для 1b.*

---

## Фаза 1c (Entitlements) — долг QA_ARCH сверх минимального DoD 1c

**Контекст:** merge гейтов и session/UI по [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md); детали и обоснование «почему не в одном PR» — раздел **«Бэклог после merge 1c»** в том же файле. **Трассировка по фазам** — таблица «Куда отнесено» там же.

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 1c-Q1 | Подтвердить/устранить лишний резолв `get_current_admin` (роутер `require_entitlement` + хендлер); иначе `request.state` / общий dependency | [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) B1 | open | Сначала проверка кэша FastAPI на запрос |
| 1c-Q2 | Единый регистр стабильных `code` в JSON (предпочтительно lower), SEC + Product, entitlement + box + публичные ошибки | [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) B2, [10_CROSS_CUTTING](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) §28 | **done** (2026-04-06) | `normalize_api_error_code` + envelope `main.py`; документ [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md); OpenAPI/полный словарь — **1c-Q4** |
| 1c-Q3 | Расширить `build-and-test-entitlements.yml` на полный `pytest tests/` (или маркеры) при готовности CI | [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) B3, [07_PHASE_2](./07_PHASE_2_RELIABILITY.md) | done | Job `full-backend-tests` в [build-and-test-entitlements.yml](../../../.github/workflows/build-and-test-entitlements.yml) |
| 1c-Q4 | Зафиксировать контракт тела 403 для гейтов (OpenAPI / docs), выравнивание регистра `code` | [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) B4, [06_PHASE_1E](./06_PHASE_1E_LIFECYCLE_EMBED.md) | **in_progress** | **2026-04-06:** компоненты в `/openapi.json`. **2026-04-06:** все операции под `api_router` получают стандартные `responses` через `STANDARD_OPENAPI_ERROR_RESPONSES` + `main.py`. **2026-04-07:** публичный embed — `POST …/assistant/message`, `POST …/rag/search`: `response_model` + примеры тел + example 400 `embed_ai_input_too_long`; регистр кодов — [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md) §Public embed. Остаток: примеры 403 гейтов и sweep прочих публичных путей |
| 1c-Q5 | Паттерн изоляции seed при мутации `organization_id` в pytest | [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) B5, [08_tests_matrix.md](../08_tests_matrix.md) | done | Текст в матрице тестов |

---

## Фаза 1e (Lifecycle / Embed §24) — долг сверх минимального DoD 1e

**Контекст:** spine Phase 1e в коде и [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md); срез Stream 1e + 3+ — [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md), [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md).

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 1e-F1 | RAG per-org §24.3: выбор vector store, SEC, негативные тесты утечки | МП **§24.3**, [06_PHASE_1E](./06_PHASE_1E_LIFECYCLE_EMBED.md), [STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md) | **partial** (2026-04-07) | v1: таблица KB + SQL по `organization_id` + публичный search; негатив: `tests/api/test_rag_org_isolation.py`. Хвост: vector store, audit KB, rate limit — в эпике §24.3 |
| 1e-F2 | AI sanitizer + tokenizer-лимиты §24.2 (не только флаги каталога) | МП **§24.2**, 06_PHASE_1E | **done** (2026-04-07) | `embed_ai_max_input_tokens` / `embed_ai_max_output_tokens`, capped body read в `public_embed` |
| 1e-F3 | UI экспорта для Основателя + автоматизация сроков/объёма | [TENANT_OFFBOARDING_AND_EXPORT.md](../../operations/TENANT_OFFBOARDING_AND_EXPORT.md), МП **§2d** п.7 | **partial** (2026-04-07) | Admin UI `/admin/data-export` + API заявок/manifest; полная автоматизация PII — Product/OPS |
| 1e-F4 | Audit-записи (БД или structured) на rotate/revoke/create embed keys и webhook secret | МП **§25**, **1a-F3** | **done** (2026-04-07) | `organization_embed_audit_log`; сервис `embed_security_audit_service` |
| 1e-F5 | Сузить RBAC управления embed (роль/permission), не только `omni.embed.bundle` | SEC + [04_PHASE_1C](./04_PHASE_1C_ENTITLEMENTS.md) | **done** (2026-04-07) | `view_embed_settings`, `manage_embed_settings` |
| 1e-F6 | Панель Grafana / алерты по `embed_public_request_total` и ошибкам inbox | [05_PHASE_1D](./05_PHASE_1D_OBSERVABILITY.md), метрика в `metrics.py` | **done** (2026-04-07) | `dental_booking_alerts.yml` + ряд в `dental_booking_observability_w1_w2.json` |
| 1e-F7 | Reverse-proxy лимит тела для `.../inbox` при отсутствии корректного `Content-Length` | QA_ARCH 1e (DoS без CL) | **done** (2026-04-07) | Потолок байт в приложении + `deploy/nginx/embed_webhook_inbox_body_limit.conf` |

**Связка с 1c:** **1c-Q4** (OpenAPI / полный контракт 403 и публичных путей) — не закрыт в рамках 1e; **1c-Q2** (нижний регистр `code`) — закрыт на уровне HTTP-обработчика и реестра-документа.

**Резюме «что делаем потом» по 1e (человекочитаемо):** [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md) — раздел **«Следующие этапы (зафиксировано QA_ARCH)»**. Статусы `open` / `done` и приоритет эпика — только в таблице этой секции.

---

## Фаза 2 (Reliability / ADR-008–009) — долг сверх минимального DoD

**Контекст:** минимальный Phase 2 и приёмка @QA_ARCH — [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md), [STREAM_PHASE2_RELIABILITY_EPICS.md](./STREAM_PHASE2_RELIABILITY_EPICS.md), ADR-008/009.

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 2-F1 | Outbox на критичные события цепочки booking / `booking_event_chain.md` (не только `PaymentSuccess`) | [07_PHASE_2](./07_PHASE_2_RELIABILITY.md), МП §17.1 | **done** (ядро, 2026-04-13) | `emit_booking_domain_event`, `get_session_booking_domain_outbox`, `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED`. **Хвост:** `patch_booking_admin` при смене `status` через PATCH не эмитит `BookingCompleted`/`Cancelled`/… в outbox — при необходимости симметрии с прямыми методами сервиса |
| 2-F2 | U-009: задокументированный drill restore + фактические RPO/RTO в §1 DR_RUNBOOK | [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md), МП | **partial** (2026-04-06) | **Сделано:** журнал учения §6.1 с датой + ссылка на workflow (не только GitHub без записи). **Хвост OPS:** целевые и фактические RPO/RTO в таблице §1 (managed DB / staging PITR) |
| 2-F3 | Полноценный dead-letter (столбец/таблица или tombstone), а не только cap по `attempts` + ручная чистка | ADR-009, отчёт QA_ARCH | open | Сейчас: `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS`, gauge `domain_outbox_blocked_by_attempt_cap_rows`, алерт |
| 2-F4 | Внешний экспорт/проверка managed-DB backup (не только `backup_logical_export_*`) | ADR-008 | open | Провайдер / отдельный job |
| 2-F5 | Тесты redelivery + идемпотентность consumer’ов по каждому типу события после миграции на outbox | [07_PHASE_2](./07_PHASE_2_RELIABILITY.md) п.3, [booking_event_chain.md](../domains/booking_event_chain.md) | **partial** (2026-04-13) | `tests/application/test_domain_outbox_platform_provision.py` + `test_domain_outbox_payment.py`: dedup, второй batch, simulate redelivery `BookingCreated`. **Хвост:** матрица по типам (`BookingCancelled`, `PaymentSuccess` side-effects в CRM/tasks), property-тесты идемпотентности handler’ов |
| 2-F6 | ADR-008/009: снять «partial» — текст ADR = факт (env, метрики, алерты) или amendment + дата | [07_PHASE_2](./07_PHASE_2_RELIABILITY.md) DoD | open | README ADR + `dental_booking_alerts.yml` |
| 2-F7 | Контур B: внедрить вариант из §4.4 при multi-replica (outbox/sticky/ADR риска) | [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.4, МП §17.1 | **partial** (2026-04-13) | Outbox-провижининг в коде (`PlatformSignupProvision`, `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED`). **Хвост OPS:** при `replicas≥2` подтвердить ingress / отсутствие расхождения с политикой §17.1 в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) |
| 2-F8 | Расширение CI за пределы entitlements workflow (e2e/security из `workflows_disabled`) | U-008, [INDEX.md](../INDEX.md) | **done** (2026-04-06) | **Решение LEAD:** [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](../../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md) — baseline релиза = `release-gate.yml` на `v*`; e2e/security из `workflows_disabled` — явный waiver до отдельного включения |

---

## Фаза 3+ (Vertical / CRM import / enterprise)

**Контекст:** минимальный каркас и ревью @QA_ARCH — [08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md), ADR-010.

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 3-F1 | Конвейер импорта: ingest → validate → staging → batch commit по §25.0 / §25.3; не только dry-run stub | МП §25, [data_migration_import_connectors.md](../modules/data_migration_import_connectors.md), ADR-010 | **done** (2026-04-07) | `crm_import_pipeline_service`, статусы `ingested` / `staged` / `committed`; см. [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md) |
| 3-F2 | Аудит смены `industry_profile` и крупных шагов импорта (кто/когда/орг) | МП §1 C5, **1a-F3** (паттерн), [08_PHASE_3_PLUS](./08_PHASE_3_PLUS.md) | **done** (2026-04-07) | `organization_industry_profile_audit`, `crm_import_job_audit` |
| 3-F3 | Выравнивание **effective organization** для остальных `require_entitlement` маршрутов (admin.organization_id vs clinic.organization_id), единый helper | **1c-Q*** / честность SaaS, отчёт QA_ARCH Phase 3+ | **partial** (2026-04-07) | `effective_organization` + CRM import; остальные админ-маршруты — хвост |
| 3-F4 | Публичный/витринный контракт vertical: i18n, feature flags, негативные тесты публичных dental API | МП §14, [08_PHASE_3_PLUS](./08_PHASE_3_PLUS.md) | open | Сейчас: admin medical gate + session field |
| 3-F5 | Grafana/алерты на `crm_import_operations_total` (аномалии, ошибки клиента) | [05_PHASE_1D](./05_PHASE_1D_OBSERVABILITY.md), МП §11 | open | Метрика добавлена в коде |
| 3-F6 | UI мастера импорта + расширение allowlist профилей источников (синхрон с ADR-010 / коннекторы) | [08_PHASE_3_PLUS](./08_PHASE_3_PLUS.md) порядок @DEV | open | API allowlist: `csv_contacts_v1`, `bitrix24_contacts_v1` |

---

## Фаза 4 (optional Commerce / §26)

**Контекст:** [09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md), [ADR-013](../../adr/ADR-013-commerce-store-bounded-context-scope.md), [domains/commerce_bounded_context.md](../domains/commerce_bounded_context.md).  
**Ревью @QA_ARCH:** зафиксировано в [09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md) и таблице **4-F*** ниже.

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 4-F1 | Зафиксировать bounded context + резерв имён + placeholder каталога (`commerce.store_network`, inactive) | МП §15b фаза 4, §26 | **done** | 2026-04-06: доменный док, ADR-013 Proposed, миграция каталога |
| 4-F2 | Первая миграция `commerce_*` + минимальный API под entitlement | ADR-013, [09_PHASE_4](./09_PHASE_4_OPTIONAL_COMMERCE.md) | **done** | 2026-04-06: overview, номенклатура, точки, **остатки**, **документы приход/расход** (`goods_in`/`goods_out`); UI `/admin/commerce` |
| 4-F3 | Read-models / витрины для сети точек (без «общей кучи» строк) | МП §26 | **done** | `GET …/organization/commerce/network-overview`, см. 09_PHASE_4 |
| 4-F4 | CSV-профили номенклатуры и остатков (1С-friendly v1) | ADR-010, МП §26, 09_PHASE_4 | **done** | `commerce_nomenclature_csv_v1`, `commerce_stock_balances_csv_v1`; полный конвейер §25 — **4-F5+** / **3-F1** |
| 4-F5 | `commerce_import_jobs`, `Idempotency-Key`, `GET …/import-jobs` | 09_PHASE_4, ADR-010 | **done** | 2026-04-06: миграция `20260421_commerce_import_jobs`; failed jobs v1 намеренно не пишем |
| 4-F5+ | Очередь/Celery, крупные файлы, failed jobs без конфликта с `get_db` | [09_PHASE_4](./09_PHASE_4_OPTIONAL_COMMERCE.md), ADR-010 | open | Как в таблице итераций фазового файла |
| 4-F6 | Сериализация импорта до первой строки (staging job / advisory lock), если нужен строгий SLO под параллельный POST | QA_ARCH Phase 4 | open | Сейчас: replay после `IntegrityError` снижает двойную запись; гонка двух воркеров до commit job теоретически возможна |
| 4-F7 | ADR-013 → **Accepted**, явная запись ворот ARCH+LEAD + ссылки на ревизии Alembic | ADR-013, 09_PHASE_4 ворота | open | Proposed → Accepted по процессу LEAD |
| 4-F8 | Выравнивание **effective organization** для Commerce (как `get_crm_import_organization_id`), если появятся админы с org только на клинике | **3-F3**, QA_ARCH Phase 4 | open | Сейчас guard: `admin.clinic_id` + `organization_id` админа |
| 4-F9 | Негативный тест **403** `commerce_clinic_org_mismatch` (существующая клиника другой org) | ADR-013 п.2 | open | Дополнение к 404 «не домашняя клиника» |
| 4-F10 | Метрики/алерты на операции импорта Commerce (аналог `crm_import_operations_total`) | [05_PHASE_1D](./05_PHASE_1D_OBSERVABILITY.md), МП §11 | open | |
| 4-F11 | Лимит тела upload на edge (большие CSV) | QA_ARCH Phase 4, **1e-F7** | open | См. reverse-proxy / ASGI |

---

## Фазы 1d–1e, 2, 3+, 4, сквозные

Долг **1c** сверх DoD — таблица выше. Для **1d–1e** и далее — по мере закрытия фаз или отчётов QA_ARCH. Якоря:

- **1d:** [05_PHASE_1D_OBSERVABILITY.md](./05_PHASE_1D_OBSERVABILITY.md); п.6 — метрики гейта каталога подписки (**1b-F6**).
- **1e:** таблица **1e-F*** выше; [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md), МП **§24**; пересечение с **1c-Q2/Q4** (коды ошибок, контракт 403 для публичных путей).
- **2:** [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md), ADR-008/009; пересечение с **1c-Q3** (полный pytest в CI).
- **3+ / 4 / сквозное:** `08_`, `09_`, `10_` (в т.ч. **1c-Q2** через §28).

---

## Сквозное arch_plan/10 (§27–§31) — долг после QA_ARCH 2026-04-06

**Отчёты приёмки (сквозное §27–§31):** [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md); статусы **10-Q*** — таблица ниже.  
**Якорь плана:** [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md).

| ID | Что доделать | Источник | Статус | Примечание |
|----|--------------|----------|--------|------------|
| 10-Q1 | Панель Grafana для `spam_blocked_total`, `security_auth_failure_total`, `security_suspicious_request_total` (срезы по `channel` / `reason` / `path_class`) | МП §11, [05_PHASE_1D](./05_PHASE_1D_OBSERVABILITY.md), §27–§28 | **done** | `deploy/grafana/dashboards/dental_booking_security_soc_w10.json`; см. `deploy/grafana/README.md` |
| 10-Q3 | Инвентаризация тестов и внутренних вызовов на «сырой» `HTTPException.detail` без HTTP boundary; выравнивание `OMNI_*` / прочих кодов в источнике или явный документ исключений | §28, **1c-Q4** | **done** | [TEST_HTTP_EXCEPTION_BOUNDARY.md](../TEST_HTTP_EXCEPTION_BOUNDARY.md); коды omni в `admin_omni_chat.py` и `omni_outbound_policy.py` — `snake_case` в источнике |
| 10-Q4 | WAF / edge для публичного signup и сканеров | МП §27, §30 | open | App-layer лимиты — в коде; edge/WAF — OPS. См. [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md) |
| 10-Q8 | Интеграционные тесты Redis для лимитов `public_platform` checkout/catalog (без только `dependency_overrides`); опционально панель Grafana для `platform_signup_intent_ttl_expired_total` (M-B9); runbook отмены «висящих» платежей YooKassa при TTL | [STREAM_CROSS_CUTTING_GO_LIVE.md](./STREAM_CROSS_CUTTING_GO_LIVE.md), **1b-F3** | open | Не блокирует merge; перед «полным» 1b-F3 / L3 |
| 10-Q5 | Сценарий нагрузки и утверждение чисел для «10k+» / честность маркетинга §30 | [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) | **in_progress** | Шаблон прогона: [LOAD_SCENARIO_MARKETING_10K.md](../../operations/LOAD_SCENARIO_MARKETING_10K.md); утверждение чисел — LEAD |
| 10-Q6 | Чеклист для новых путей в обход `require_permissions`: ручной RBAC должен вызывать актуальные методы `RbacServiceImpl` (регрессия: несуществующий `get_admin_permissions` на SSE) | QA_ARCH 2026-04-06 | **done** | [RBAC_MANUAL_PATHS_CHECKLIST.md](../../operations/RBAC_MANUAL_PATHS_CHECKLIST.md) |
| 10-Q7 | Провязка OpenAPI: стандартные тела ошибок на операциях API v1 | §28, **1c-Q4** | **done** | Глобально для всех путей `api_router`: `STANDARD_OPENAPI_ERROR_RESPONSES` в [`src/core/openapi_error_schemas.py`](../../../src/core/openapi_error_schemas.py), монтирование в [`src/main.py`](../../../src/main.py); смок: `tests/core/test_openapi_error_schemas.py`. Примеры в `responses` — по желанию (остаток **1c-Q4**) |

*Контракт тел ошибок в OpenAPI (**1c-Q4**) в эту таблицу не дублируется — см. фазу 1c; остаток 1c-Q4 пересекается с **10-Q7**.*

---

**Обновление 2026-04-07 (cross-cutting go-live):** **1b-F3** → `in_progress`; новая строка **10-Q8** (Redis-интеграция тестов лимитов, Grafana M-B9, runbook YooKassa); см. [STREAM_CROSS_CUTTING_GO_LIVE.md](./STREAM_CROSS_CUTTING_GO_LIVE.md).

## Правило ведения (LEAD + QA_ARCH)

1. Новая строка добавляется, когда **QA_ARCH** или **ARCH** фиксирует расхождение «DoD закрыт» vs «целевой образ / честность МП не достигнута».  
2. Перед началом эпик-среза **ARCH** проверяет, нет ли уже строки с тем же смыслом (избегать дублей с МП).  
3. Статус `done` — только с ссылкой на PR/миграцию/ADR amendment.

**Версия файла:** 2026-04-07 (вечер) — **1e-F1…F7** и **3-F1…F3** пересмотрены по срезу Stream 1e + Phase 3+ ([STREAM_PRODUCT_RAG_24_EPIC.md](./STREAM_PRODUCT_RAG_24_EPIC.md), [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md)). Утром того же дня: **1b-F2/F6/F10** закрыты, добавлены **1b-F6a, F11, F12**; pytest контура B — `tests/api/test_platform_billing.py`. **2026-04-06:** scratch-файлы `docs/artifacts/QA_ARCH_*.md` удалены; единая сводка замен и усилений **1a-E2** — [IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md](../../artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md). Навигация эпик-срезов: [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md), `STREAM_*_EPICS.md`, [OBSERVABILITY_COMPOSE_SMOKE.md](../../operations/OBSERVABILITY_COMPOSE_SMOKE.md), [SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md](../SAAS_EPIC_PRIORITY_DECISION_1A_VS_1B.md).
