# DEV_PROMPTS — AI‑модуль (ассистент, коуч, безопасность)

> Основание: `ARCH_AI_POLICY.md`, `ARCH_AI_IMPLEMENTATION.md`  
> Цель: поэтапно внедрить безопасный, настраиваемый AI‑слой без ломки текущего функционала.

---

## 0. Общие правила

- Не менять существующее поведение, если это не описано явно (особенно отправку сообщений и логику чата).
- Все вызовы внешнего AI проходят только через `SafeAiClient` (не `AiClient` напрямую).
- Не отправлять в AI телефоны, email, ФИО и другие ПДн — доверяем только текст после санитизации.
- При любой ошибке парсинга JSON от AI — лог, graceful fallback, никакой паники для пользователя.

---

## ФАЗА 1 — `AiSanitizer` + `SafeAiClient` + интеграция в ChatAiService

### Задача 1.1 — Реализовать `AiSanitizer`

- **Файл:** `src/core/ai_sanitizer.py`
- **Действия:**
  - Создать класс `AiSanitizer` и dataclass `SanitizedText` как в `ARCH_AI_IMPLEMENTATION.md`.
  - Покрыть базовыми regexp:
    - телефоны;
    - email‑ы;
    - оставить TODO/комментарий для расширения на ФИО.
  - Написать unit‑тесты на несколько кейсов (телефон, email, смешанный текст).

### Задача 1.2 — Реализовать `SafeAiClient`

- **Файл:** `src/infrastructure/external_apis/safe_ai_client.py`
- **Действия:**
  - Обёртка над `AiClient` с:
    - методом `is_configured()`;
    - методом `complete(payload, text_keys)`:
      - проходит по указанным ключам и применяет `AiSanitizer` (минимум через явную обработку `messages[n].content`).
  - Этими ключами на первом этапе можно считать:
    - `"messages[].content"` — достаточно обработать все `payload["messages"][i]["content"]`.

### Задача 1.3 — Перевести `ChatAiService` на `SafeAiClient`

- **Файл:** `src/application/services/chat_ai_service.py`
- **Действия:**
  - В `__init__` вместо `self.ai_client = AiClient()` ввести:
    - `self.safe_ai_client = SafeAiClient(ai_client or AiClient())`.
  - В методах `summarize_conversation`, `suggest_reply`, `analyze_patient`:
    - заменить `self.ai_client.complete(payload)` на `self.safe_ai_client.complete(payload, text_keys=["messages[].content"])`.
  - Убедиться, что fallback‑логика при не сконфигурированном AI (`is_configured()`) осталась.

> **Критерий завершения Фазы 1:** все существующие AI‑фичи продолжают работать, но любые отправляемые в AI тексты проходят через санитайзер.

---

## ФАЗА 2 — Настройки AI на уровне клиники

### Задача 2.1 — Добавить таблицу `clinic_ai_settings`

- **Миграция:** `alembic/versions/add_clinic_ai_settings.py`
- **Действия:**
  - Создать таблицу по схеме из `ARCH_AI_IMPLEMENTATION.md` (п. 1.1).
  - Обеспечить `UNIQUE (clinic_id)`.

### Задача 2.2 — Реализовать `ClinicAiSettingsService`

- **Файл:** `src/application/services/clinic_ai_settings_service.py`
- **Функционал:**
  - `get_or_create_default(clinic_id)`:
    - если записи нет — создать с дефолтами: `ai_enabled=False`, `ai_mode="draft_only"`, пустые списки.
  - `update_settings(clinic_id, payload)`:
    - валидировать `ai_mode`, `ai_allowed_intents`, структуру `ai_autoreply_hours`.
    - сохранить изменения.
  - `get_effective_prompt(clinic_id)`:
    - получить `clinic` и её `business_type`;
    - собрать:
      - базовый системный промпт (жёстко в коде),
      - бизнес‑специфичный (по `business_type`),
      - пользовательский `ai_business_prompt`;
    - вернуть одну строку.

### Задача 2.3 — API для настроек AI

- **Файл:** `src/api/v1/routers/admin_ai_settings.py`
- **Эндпоинты:**
  - `GET /v1/admin/clinics/{clinic_id}/ai-settings`
  - `PUT /v1/admin/clinics/{clinic_id}/ai-settings`
- **Важно:**
  - не отдавать ключи/URL провайдера в ответ;
  - держать контракт в синхроне с `ARCH_AI_IMPLEMENTATION.md` (п. 3.1).

> **Критерий Фазы 2:** владелец может через API прочитать/обновить настройки AI для клиники; промпт собирается с учётом типа бизнеса и кастомного текста.

---

## ФАЗА 3 — JSON‑форматы ответов AI и их парсинг

### Задача 3.1 — DTO для JSON‑ответов

- **Файл:** `src/application/dto/chat_ai_dto.py`
- **Действия:**
  - Добавить/обновить модели:
    - `ConversationSummaryResponse` → поля из `ARCH_AI_POLICY.md` (summary, sentiment, main_issue, is_conflict, is_resolved, suggested_actions).
    - `SuggestReplyResponse` → `variants: list[str]`.
    - `PatientAiInsight` → уже есть, убедиться, что соответствует формату (summary, risk_flags, next_best_action).

### Задача 3.2 — Обновить промпты и парсинг в `ChatAiService`

- **Файл:** `src/application/services/chat_ai_service.py`
- **Действия:**
  - Для каждого метода:
    - явно просить модель: “верни строго JSON в формате: {...} без пояснений”.
    - после вызова AI:
      - `json.loads(content)` → валидация через Pydantic‑модель;
      - в случае ошибки:
        - лог (`logger.exception` c payload’ом без ПДн);
        - возврат простого fallback (как сейчас).

> **Критерий Фазы 3:** backend хранит внутреннее представление AI‑ответов в структурированном виде; фронту не ломаем текущий контракт, а усиливаем его.

---

## ФАЗА 4 — AI‑коуч и отчёты по конфликтам

### Задача 4.1 — Таблица `conversation_ai_analysis`

- **Миграция:** `alembic/versions/add_conversation_ai_analysis.py`
- Реализовать схему из `ARCH_AI_IMPLEMENTATION.md` (п. 1.2).

### Задача 4.2 — `ConversationAnalysisService`

- **Файл:** `src/application/services/conversation_analysis_service.py`
- **Функции:**
  - `analyze_range(clinic_id, date_from, date_to)`:
    - выбрать диалоги за период;
    - сформировать компактный контекст для каждого (последние N сообщений, без ПДн — через `AiSanitizer`);
    - вызвать AI с промптом “проанализируй эти диалоги и верни JSON по схеме items+summary”;
    - распарсить JSON и записать `conversation_ai_analysis`.

### Задача 4.3 — API отчётов

- **Файл:** `src/api/v1/routers/admin_ai_reports.py`
- Эндпоинты:
  - `GET /v1/admin/ai-reports/conflicts` — выборка из `conversation_ai_analysis` с фильтрами.
  - `POST /v1/admin/ai-reports/conflicts/reanalyze` — триггер `ConversationAnalysisService.analyze_range`.

> **Критерий Фазы 4:** владелец может получить отчёт по конфликтам/жалобам за период, основанный на хранимых в БД результатах AI‑анализа.

---

## ФАЗА 5 — Страница настроек AI и интеграция на фронте

### Задача 5.1 — `AdminAiSettingsPage`

- **Файл:** `frontend/src/admin/pages/AdminAiSettingsPage.tsx`
- **Функционал:**
  - Вызов `GET/PUT /admin/clinics/{clinic_id}/ai-settings` через `react-query`.
  - UI для:
    - `ai_enabled`, `ai_mode`, `ai_autoreply_enabled`;
    - `ai_business_prompt` (textarea);
    - `ai_allowed_intents` (multiselect);
    - `ai_autoreply_hours` (UI‑контрол выбора интервалов).

### Задача 5.2 — Лёгкая интеграция с существующими страницами

- `AdminChatPage`:
  - отобразить текст “AI выключен / только черновики / автоответ включён” где‑нибудь в шапке/под заголовком;
  - для будущего: хранить в UI флаг, что данный ответ был предложен AI (по данным backend).
- `AdminPatientsPage`:
  - UI уже использует `PatientAiInsight`; убедиться, что новые поля отображаются корректно (summary + next_best_action).

> **Критерий Фазы 5:** владелец может сам включить/выключить AI, настроить его поведение и видеть статус в админке.

---

## ФАЗА 6 — (опционально) поддержка on‑prem провайдера

Если появится заказ на on‑prem:

- Добавить поддержку `ai_provider_type = "on_prem"`:
  - `AiClient` читает другой `base_url` (внутренний).
  - политика санитизации может быть ослаблена по решению @SEC/@LAWYER (но код должен это поддерживать конфигом).
- Добавить проверку в `admin_ai_settings`: `ai_provider_type` меняется только пользователями с ролью владельца/суперадмина.

