# DEV_PROMPTS — @QA: скидки, прайс и AI

> Цель: чтобы @QA работал по чек‑листу и выдавал только финальный отчёт, без диалогов с пользователем.

---

## 0. Режим работы @QA

- Не вести переписку с пользователем во время прогона.
- Работать строго по этому документу + `ROLE_QA.md`, `ARCH_TESTS_FULL.md`, `ARCH_TESTS.md`.
- На выходе — **один** структурированный отчёт в формате из `ROLE_QA.md` (раздел "Формат отчёта"), без промежуточных комментариев.

---

## 1. Область тестирования

- **Модуль скидок и ценообразования:**
  - Backend:
    - `PricingService` (`src/application/services/pricing_service.py`);
    - `PaymentService.create_payment` (`src/application/services/payment_service.py`);
    - public/admin services API:
      - `src/api/v1/routers/public_services.py`,
      - `src/api/v1/routers/admin_services.py`,
      - DTO `service_dto.py`.
  - Frontend:
    - `frontend/src/app/pages/BookingWizardPage.tsx`;
    - `frontend/src/admin/pages/AdminServicesPage.tsx`;
    - `frontend/src/admin/pages/SchedulePage.tsx`.

- **AI‑модуль:**
  - Санитизация и вызовы AI:
    - `src/core/ai_sanitizer.py`;
    - `src/infrastructure/external_apis/safe_ai_client.py`;
    - `src/application/services/chat_ai_service.py`.
  - Настройки AI:
    - `clinic_ai_settings` (entity + миграция);
    - `ClinicAiSettingsService`;
    - API `/v1/admin/clinics/{id}/ai-settings`;
    - `frontend/src/admin/pages/AdminAiSettingsPage.tsx`.
  - AI‑отчёты:
    - `conversation_ai_analysis` (entity + миграция);
    - `ConversationAnalysisService`;
    - API `/v1/admin/ai-reports/conflicts`, `/reanalyze`.

---

## 2. To‑dos @QA (пошагово)

### Шаг 1. API‑smoke по скидкам и прайсу

1. Поднять backend с актуальными миграциями и демо‑данными.
2. Проверить:
   - `GET /api/v1/public/clinics/{clinic_id}/services`:
     - без активных скидок: `price == base_price == effective_price`, `has_active_discount=false`;
     - с активной `period`‑скидкой: `effective_price < base_price`, `has_active_discount=true`.
   - `GET /api/v1/admin/clinics/{clinic_id}/services`:
     - формат `AdminServiceRead.service` содержит новые поля цен;
     - старые поля (`price`) не пропали.
   - `POST /api/v1/payments` (через создание брони):
     - проверить `original_amount/discount_amount/final_amount` для кейсов: без скидки, с периодической скидкой.

### Шаг 2. E2E по скидкам и оплате

1. Полный сценарий без скидки:
   - клиент выбирает услугу, врача, слот → создаёт запись → если включена предоплата → создаётся платёж без скидки.
2. Полный сценарий с активной `period`‑скидкой:
   - цена услуги в UI (BookingWizardPage, AdminServicesPage, SchedulePage) показывает `base_price → effective_price`;
   - сумма предоплаты (YooKassa) совпадает с `effective_price`.
3. Регрессия:
   - выключенная предоплата (`prepayment_enabled=false`) — запись подтверждается без платёжного шага, скидки не ломают логику статусов.

### Шаг 3. API‑smoke по AI‑модулю

1. При отключённом AI (нет `AI_PROVIDER_BASE_URL`):
   - `/api/v1/admin/chat/conversations/{id}/ai-summary` → корректный fallback `ConversationSummaryResponse`;
   - `/ai-suggest-reply` → `SuggestReplyResponse` с хотя бы одним вариантом;
   - `/admin/patients/{id}/ai-insight` → `PatientAiInsight` с локальной эвристикой.
2. При настроенном AI (по возможности на тестовом ключе):
   - убедиться, что ответы — валидный JSON, парсятся в DTO без 500.

### Шаг 4. E2E по AI‑ассистенту

1. `AdminChatPage`:
   - кнопка "AI‑резюме":
     - при нажатии появляется summary, UI не ломается, ошибки AI не приводят к падению;
   - кнопка "AI‑ответ":
     - варианты подставляются в поле ввода, **не отправляются автоматически**.
2. `AdminPatientsPage`:
   - кнопка "AI‑обзор":
     - отображает summary + next_best_action (если есть);
     - при ошибке AI — понятное сообщение, не ломает таблицу.

### Шаг 5. Настройки AI (clinic_ai_settings)

1. API:
   - `GET /v1/admin/clinics/{id}/ai-settings` для клиники без настроек — возвращает дефолты (ai_enabled=false, ai_mode="draft_only");
   - `PUT /v1/admin/clinics/{id}/ai-settings`:
     - принимает только допустимые `ai_mode` и `ai_allowed_intents`;
     - на невалидных значениях отдаёт 400.
2. UI:
   - `AdminAiSettingsPage`:
     - корректно загружает/сохраняет настройки;
     - отображает текущий `ai_provider_type`;
     - ведёт себя предсказуемо при смене выбранной клиники.

### Шаг 6. AI‑отчёты и коуч по конфликтам

1. Вызвать `POST /v1/admin/ai-reports/conflicts/reanalyze` на небольшой диапазон дат.
2. Убедиться, что:
   - появляются записи в `conversation_ai_analysis`;
   - `GET /v1/admin/ai-reports/conflicts` возвращает `summary` + `items` по схеме;
   - при отсутствии AI‑провайдера сервис не падает, а пишет в логи и возвращает разумный ответ/пустой список.

### Шаг 7. Проверка санитизации ПДн

1. Локально включить детализированные логи запросов к внешнему AI (dev‑режим).
2. Инициировать:
   - AI‑резюме диалога;
   - AI‑обзор пациента.
3. В логах запросов к AI убедиться:
   - телефоны и email заменены на `[PHONE]` / `[EMAIL]`;
   - нет “сырых” ФИО/телефонов в `messages[].content`.

---

## 3. Формат финального отчёта

- Использовать шаблон из `docs/ROLE_QA.md` (раздел "ФОРМАТ ОТЧЁТА").
- Обязательные секции:
  - **Скидки** — результаты шагов 1–2.
  - **AI‑ассистент** — шаги 3–4.
  - **AI‑отчёты** — шаг 6.
  - **ПДн/санитизация (QA‑взгляд)** — шаг 7.
- Все P0/P1 дефекты по этим областям описать с шагами воспроизведения и ссылками на логи (если есть).

