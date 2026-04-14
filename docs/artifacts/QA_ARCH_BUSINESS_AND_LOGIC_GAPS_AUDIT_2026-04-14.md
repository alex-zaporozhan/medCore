# QA_ARCH + LEAD — аудит бизнес- и логических упущений (2026-04-14)

Прогон по коду и явным комментариям в `dental_booking`, усиленный LEAD-ревью.  
Цель: зафиксировать разрывы между целевым продуктовым поведением и фактической реализацией в API, асинхронке, UI и тест-контуре.

---

## 0. Краткий вердикт LEAD по работе QA_ARCH

QA_ARCH зафиксировал базовый пласт рисков корректно.  
Что усилено в этом документе дополнительно:

1. Добавлена приоритизация (`Critical` / `High` / `Medium`) по влиянию на выручку и репутационный риск.
2. Добавлены пропущенные риски:
   - невалидируемый `return_url` в публичном checkout;
   - ручная выдача raw owner invite токена через founder API как временный обход (операционный debt);
   - недетерминированный тест-контур (часть прогонов может уходить в `skip` при недоступной инфраструктуре).
3. Добавлен явный разрыв «реал-тайм владельца» как **SLA и UX цепочка**, а не только «есть endpoint/нет endpoint».

---

## 1. Регистрация «настоящего владельца бизнеса» (real time)

### 1.1. Как устроено сейчас (факт по коду)

**Публичный контур SaaS (contour B):**

1. `POST /api/v1/public/platform/signup/checkout` (`src/api/v1/routers/public_platform_signup.py`) создаёт `platform_signup_intents` и payment URL.
2. После webhook YooKassa выполняется `execute_platform_provision` (`src/application/services/platform_billing_service.py`):
   - создаются `Organization` + первая `Clinic`;
   - создаётся owner-админ через `_provision_owner_invite`;
   - генерируется one-time invite token (хранится hash + expiry).
3. `POST /api/v1/public/platform/owner-invite/accept` (`src/api/v1/routers/public_platform_owner_invite.py`) устанавливает пароль, очищает token hash.

**Закрытый founder-контур:**

- Управление очередью провижининга, retry/manual close и mint owner invite token — `src/api/v1/routers/platform_internal.py`.
- Founder auth + MFA — `src/api/v1/routers/platform_founder_auth.py`.

Вывод: регистрации «вообще нет» — неверно. Есть checkout-driven регистрация.  
Но отдельного бесплатного onboarding потока и полноценного UI-потока для founder sales ops нет.

### 1.2. Главный разрыв (Critical) — статус после LEAD

**Было:** обещание в UI ≠ автоматическая доставка инвайта.

**Сейчас (MVP):** после провижининга ставится outbox-событие owner-invite email, драйн в webhook B, метрики `platform_owner_invite_email_total` и `platform_owner_invite_accept_total`, алерты в `dental_booking_alerts.yml`, публичный статус intent и страница accept. Histogram latency signup→delivery — по дорожной карте.

Остаётся операционный риск: без SMTP / без `PLATFORM_OWNER_INVITE_PUBLIC_BASE_URL` письмо не уйдёт (retry в outbox + метрики/логи).

### 1.3. Дополнительные owner-edge cases (High)

- `High`: при пустом `email` в intent owner admin не создаётся (`_provision_owner_invite` skip).
- `High`: занятый email приводит к `platform_signup_owner_email_already_registered`, затем retry/DLQ; нет продуктового сценария merge/reclaim/change-email.
- `High`: founder endpoint `/signup-intents/{id}/owner-invite-token` возвращает raw token (операционно нужно, но повышает требования к секретному обращению и журналам доступа).

---

## 2. Дополнительные логические упущения (расширено LEAD)

### 2.1. Платежи / безопасность / redirect

- **Закрыто по allowlist:** `PLATFORM_CHECKOUT_RETURN_URL_ALLOWLIST` + 400 `return_url_not_allowed`; счётчик `platform_checkout_rejected_total{reason=…}`.
- **Production contour A/B:** при `APP_ENV=production` пустые критичные секреты блокируют старт API (`assert_required_security_secrets_in_production`). В `/metrics` gauge `payment_webhook_governance_state{contour=patient|platform}` — снимок при старте (1 = секрет задан), чтобы не гадать по логам.
- **Dev/MVP:** без production пустой `PATIENT_PAYMENT_WEBHOOK_SECRET` по-прежнему допустим для контура A (legacy); это осознанный режим разработки.

### 2.2. Идентичность и сессии

- `Medium`: в `auth_service.py` ревокация JWT intentionally not implemented (blacklist/versioning нет) — слабый контроль экстренного отзыва.

### 2.3. Мультитенантность интеграций

- `High`: `integrations_gateway.py` использует first-clinic mapping для части webhook (MVP), что логически неверно для multi-clinic org.

### 2.4. Доменные блоки с явными MVP/Stub-debt

- `Medium`: omnichannel нормализация и канал-стабы (`omnichannel_chat_service.py`, `integration_gateway_service.py`).
- `Medium`: CRM import через `bitrix24_stub` (`admin_crm_import.py`).
- `Medium`: public commerce без цен/остатков (`public_commerce.py`).
- `Medium`: loyalty fixed-percent/stub и недореализованный family redirect (`loyalty_event_handlers.py`, `loyalty_campaign_engine.py`).
- `Medium`: booking completion TODO по скидкам/кошельку/payroll/consumables (`booking_completion_service.py`).
- `Low/Medium`: schedule допущение одного непрерывного интервала (`schedule_service.py`).
- `Medium`: admin forms имеют `form_send_link_stub` при ненастроенном канале.

### 2.5. Compliance и data lifecycle

- `Medium`: удаление пациента — soft delete без выделенного end-to-end сценария прав субъекта ПДн на анонимизацию/удаление.

### 2.6. Наблюдаемость и эксплуатация

- `Medium`: технические метрики provisioning/outbox есть, но может отсутствовать формализованный operations loop на `dead_letter`/`stuck`.

### 2.7. Тестовый контур и достоверность «зелёного» статуса (добавлено LEAD)

- **Частично закрыто:** маркер `critical_path`, workflow `critical-path-gate.yml`, `CRITICAL_PATH_CI=1` (fail вместо skip по БД/Redis для строгого профиля), junit + `scripts/ci/assert_pytest_junit_xml_gate.py`, артефакт отчёта в GHA, smoke `/signup/owner-invite` после async-тестов.
- Полный suite по-прежнему может давать skip/flake на инфраструктуре — это не отменяет отдельный reliability-трек.

---

## 3. Что можно было сделать лучше в исходном QA_ARCH

1. Явно разделить «реализация endpoint есть» и «продуктовый SLA цепочки есть» (delivery, UX finish, support fallback).
2. Сразу маркировать severity/priority, чтобы roadmap формировался от риска, а не по списку.
3. Включить тест-контур как часть бизнес-риска: `skip` в critical сценариях = непроверенная поставка.
4. Для каждого упущения добавлять «детектор» (метрика, алерт, acceptance test), иначе риск неуправляем.

---

## 4. Приоритетный список к закрытию

1. `Critical`: автоматизированная доставка owner invite + постоплатный UX завершения входа.
2. `High`: allowlist/политика для checkout `return_url`.
3. `High`: anti-skip тест-гейт для критических потоков (signup/provision/invite accept).
4. `High`: webhook secret governance в проде (contour A/B).
5. `High`: корректная tenant-маршрутизация входящих интеграционных webhook.

---

## 5. Ссылка на план реализации

Исполнимый план решений A→B со стадиями, тестами и метриками:  
`docs/artifacts/LEAD_DECISIONS_IMPLEMENTATION_ROADMAP_A_TO_B_2026-04-14.md`

---

## 6. QA_ARCH follow-up после реализации LEAD (2026-04-14)

### Закрыто/усилено

- Добавлен `return_url` hardening для checkout: allowlist host + проверка схемы `http/https`.
- Добавлен публичный статус intent (`GET /public/platform/signup/intents/{id}/status`) для post-payment UX.
- Усилен outbox доставки owner invite:
  - для временных infra/config ошибок (`smtp_not_configured`, пустой public base URL) теперь не «тихий успех», а deferred retry;
  - инкрементируются `attempts`, чтобы работал cap и наблюдаемость.
- Снижен риск хранения чувствительных данных: после terminal/success обработки owner-invite события `token` вычищается из payload outbox.
- Добавлены production-safe авто-дефолты в `Settings`:
  - derive `platform_checkout_return_url_allowlist` из return URL;
  - derive `platform_owner_invite_public_base_url` из return URL (если явно не задано).

### Остаточные риски

- В dev/CI локально встречаются нестабильности БД на полном прогонах (`deadlock`/`connection closed` в `truncate_tables`), из-за чего часть suite может падать не по бизнес-логике. Это отдельный reliability-трек (A3), не регрессия бизнес-кода.

### QA_ARCH follow-up (2026-04-14, второй проход)

**Сделано в коде по своим рекомендациям:**

- Метрика **`platform_checkout_rejected_total{reason}`** при отклонении checkout (в т.ч. `return_url_not_allowed`, `return_url_missing`).
- Gauge **`payment_webhook_governance_state{contour}`** на старте — снимок «секрет задан», вместо ручной сверки env в проде (Grafana/Prometheus).
- Тест на инкремент счётчика при allowlist; тест на gauge; тесты CLI **junit gate** (`tests/core/test_junit_xml_gate_script.py`).
- Workflow **critical-path-gate**: загрузка артефакта `reports/` при любом исходе.

**Остаётся (не маскировать):**

- **B1** multi-tenant routing в integrations — без изменений.
- **Break-glass** founder raw token, **JWT revoke**, **data lifecycle** — в бэклоге.
- Контур owner-invite: счётчики + гистограмма `platform_signup_to_invite_delivery_seconds` + алерты (`PlatformOwnerInvite*`) в `deploy/prometheus/dental_booking_alerts.yml`; runbook — `docs/operations/PLATFORM_BILLING_PROVISION_RECONCILE.md` § Owner invite.

---

*Документ усилен LEAD-ревью; актуализировать при изменении критических потоков auth/billing/provisioning/test-gates.*
