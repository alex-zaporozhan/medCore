## ARCH_DEV_OMNI_POLICY_016 — политика ПД и AI‑провайдеров

> DEV_PROMPT_OMNI_POLICY_016 — «политика ПД и AI‑провайдеров (OMNI‑2, SEC‑1)»

---

## 1. Контекст и существующее состояние

### 1.1. Где сейчас живёт политика AI

- **Сущности и конфиг:**
  - `ClinicAiSettings` (`src/domain/entities/clinic_ai_settings.py`):
    - `ai_enabled`, `ai_tasks_enabled`, `ai_mode`, `ai_business_prompt`, `ai_allowed_intents`,
    - `ai_autoreply_enabled`, `ai_autoreply_hours`,
    - `ai_provider_type: "external" | "ru_compliant" | "on_premise"`.
  - `AiProviderConfig` + `AiConfigService.get_clinic_ai_config` (`src/application/services/ai_config_service.py`):
    - `base_url/api_key/model` из глобальных `settings`;
    - `provider_type` и `allow_personal_data` вычисляются на основе `ClinicAiSettings`:
      - `provider_type = row.ai_provider_type or "external"`;
      - `allow_personal_data = bool(row.ai_enabled and provider_type in {"ru_compliant", "on_premise"})`.
- **Санитайзер:**
  - `AiSanitizer` (`src/core/ai_sanitizer.py`):
    - по умолчанию вырезает телефон/e‑mail (`[PHONE]`, `[EMAIL]`);
    - при `allow_personal_data=True` работает в режиме pass‑through.
- **Безопасный клиент и фабрика:**
  - `SafeAiClient` (`src/infrastructure/external_apis/safe_ai_client.py`):
    - оборачивает `AiClient`;
    - всегда применяет `AiSanitizer` к `messages[n].content` перед внешним вызовом;
    - предоставляет метод `chat_with_tools`, который санитизирует `AgentChatMessage.content` перед вызовом провайдера.
  - `build_safe_ai_client` (`src/application/services/ai_client_factory.py`):
    - центральная фабрика `SafeAiClient` по `clinic_id` и `AsyncSession`;
    - использует `AiConfigService.get_clinic_ai_config` для вычисления `provider_type` и `allow_personal_data`;
    - в режимах без `clinic_id`/сессии создаёт строгий конфиг (`provider_type="external"`, `allow_personal_data=False`).

### 1.2. Где и как сейчас вызывается AI

Основные места (после внедрения политики):

- **Omnichannel:**
  - `OmnichannelAiOrchestrator` (`src/application/services/omnichannel_ai_orchestrator.py`):
    - для `run_ai_agent` использует `build_safe_ai_client(clinic_id, session)` и `SafeAiClient.chat_with_tools`;
    - для legacy‑режима (`LLMClient`) работает через `SafeAiClient`, сконфигурированный по фабрике.
- **Легаси Chat AI:**
  - `ChatAiService` (`src/application/services/chat_ai_service.py`):
    - лениво инициализирует `SafeAiClient` через `build_safe_ai_client(self.ctx.clinic_id or self.ctx.user_id, session)`;
    - все внешние вызовы (`summarize_conversation`, `suggest_reply`, `analyze_patient`) используют один и тот же клиент.
- **AI‑отчёты и анализ диалогов:**
  - `ConversationAnalysisService` (`src/application/services/conversation_analysis_service.py`):
    - лениво инициализирует `SafeAiClient` через `build_safe_ai_client(self.ctx.clinic_id or self.ctx.user_id, session)`;
    - анализ диалогов (`analyze_range`) работает только при сконфигурированном провайдере.
- **AI‑Task‑generator (Celery):**
  - `ai_tasks.py` (`src/infrastructure/messaging/tasks/ai_tasks.py`):
    - для глобальной аналитики использует `build_safe_ai_client(clinic_id=None, session=None)` в строгом режиме без ПД;
    - в случае ошибок провайдера (`AiClientError`) делает безопасный no‑op без падения джобы.
- **Админ‑эндпоинты статуса и отчётов:**
  - `admin_ai_status.py` и `admin_ai_reports.py`:
    - используют `build_safe_ai_client` для определения, доступен ли внешний AI‑провайдер для конкретной клиники или глобально.

**Вывод:** все внешние AI‑вызовы проходят через связку `AiConfigService` → `build_safe_ai_client` → `SafeAiClient`/`AiSanitizer`;  
прямое создание `AiClient` вне этих слоёв устранено для рабочих путей Omnichannel/Chat/Analytics/Tasks/Admin.

---

## 2. Целевое состояние политики (что должно быть после задачи)

### 2.1. Жёсткие инварианты политики AI

1. **Все внешние AI‑вызовы идут только через SafeAiClient.**
   - Прямое использование `AiClient` для внешних запросов в коде запрещено (кроме случаев, когда он обёрнут в `SafeAiClient` в том же месте).

2. **Все места, где формируется `AiProviderConfig`, используют `AiConfigService` и `ClinicAiSettings`.**
   - Никаких ad‑hoc чтений `ClinicAiSettings` или глобальных `settings` для AI‑URL/ключа, минуя `AiConfigService`.

3. **Политика ПД реализована строго по `BUSINESS_LOGIC_V2`:**
   - `provider_type = "external"` → `allow_personal_data=False` (всегда, даже если админ включил ai_enabled);
   - `provider_type = "ru_compliant" | "on_premise"` + `ai_enabled=True` → `allow_personal_data=True`;
   - при `allow_personal_data=False`:
     - `AiSanitizer` маскирует телефоны/почты минимум так, как сейчас (`[PHONE]`, `[EMAIL]`);
     - любые дополнительные поля с ПД (ФИО и т.п.) либо не передаются, либо маскируются в будущем расширении.

4. **Режим работы AI для конкретной клиники читается через `ClinicAiSettings`/`ClinicAiSettingsService` и не дублируется в других местах.**
   - Настройки в админке (`/admin/ai-settings`) — единственная точка для конфигурирования;
   - Omnichannel/AI, аналитика, AI‑tasks используют эти же настройки.

### 2.2. Наблюдаемость и отказоустойчивость

1. Все AI‑вызовы (через `SafeAiClient`) логируют:
   - факт использования клиента и ключевые параметры политики (`clinic_id`, `provider_type`, `allow_personal_data`);
   - ошибки провайдера (через метрики `omni_ai_provider_errors_total` с `source` = `omni_orchestrator` / `legacy_chat_ai_*` / `ai_tasks` и т.п.).
2. При любой ошибке AI‑провайдера:
   - сервисы не падают 5xx без объяснения;
   - используют fallback (где определён) или no‑op;
   - добавляют контекст в лог/метрики, но без утечки ПД.

---

## 3. Детальный архитектурный план изменений

### 3.1. Консолидация использования AiClient/SafeAiClient

**Шаг 1. Инвентаризация всех прямых `AiClient(...)` в коде.**

- Ожидаемые места (по текущему коду):
  - `chat_ai_service.py` (уже оборачивает в `SafeAiClient` — оставить, но привести к единому стилю);
  - `conversation_analysis_service.py` (аналогично);
  - `omnichannel_ai_orchestrator.py` (используется в `LLMClient` и `run_ai_agent` — нужно унифицировать);
  - `ai_tasks.py` (наиболее рискованное место — прямой `AiClient()` в Celery‑таске).

**Шаг 2. Ввести единый helper для создания SafeAiClient по clinic_id.**

- Новый модуль/функция (например, `src/application/services/ai_client_factory.py` или статическая функция в `AiConfigService`):
  - `async def build_safe_ai_client(clinic_id: UUID, session: AsyncSession | None = None) -> SafeAiClient:`
    - использует `AiConfigService(session).get_clinic_ai_config(clinic_id)`;
    - создаёт `AiClient(config=config)`;
    - создаёт `AiSanitizer(allow_personal_data=config.allow_personal_data)`;
    - возвращает `SafeAiClient(base_client, sanitizer)`.
- Все места, где сейчас связываются `AiConfigService` + `AiClient` + `AiSanitizer` вручную, переводятся на этот helper.

**Шаг 3. Для контекстов без clinic_id (глобальные аналитические задачи)**

- Явно определить политику:
  - либо использовать «глобальный» clinic‑like ID (например, по ClinicAiSettings для конкретной клиники, если это всегда clinic‑аналитика);
  - либо использовать safe‑дефолт:
    - `provider_type="external"`, `allow_personal_data=False` (строгий режим),
    - держа эту логику централизованно в `AiConfigService`/helper’е.

### 3.2. Жёсткая реализация политики allow_personal_data

**Шаг 4. Уточнить/подтвердить логику в `AiConfigService`.**

- Проверить, что:
  - `provider_type` берётся только из `ClinicAiSettings.ai_provider_type`, с дефолтом `"external"`;
  - `allow_personal_data` вычисляется ровно как:
    - `row.ai_enabled and provider_type in {"ru_compliant", "on_premise"}`;
    - для всех остальных режимов — строго `False`.
- Если в коде есть другие места, где `allow_personal_data` задаётся руками — удалить/заменить на использование `AiConfigService`.

**Шаг 5. Расширить AiSanitizer при необходимости.**

- Для v1 достаточно текущего поведения (телефон/email);  
  архитектурно заложить:
  - возможность добавить маскирование ФИО/паспортных/адресов в будущем (расширяемый регекс/плагины);
  - но не менять это, пока нет чётких требований (@SEC/@BIZ).

### 3.3. Выравнивание всех AI‑клиентов под новую политику

**Шаг 6. Omnichannel AI Orchestrator (`omnichannel_ai_orchestrator.py`).**

- Все места, где создаётся `AiClient` или `SafeAiClient`, заменить на:
  - `safe_client = await build_safe_ai_client(clinic_id, session)` (или аналогичный helper).
- Убедиться, что:
  - `clinic_id` передаётся корректно (обычно через `chat.business_account_id` или контекст);
  - нет альтернативных путей обхода (например, создание `AiClient()` без конфигурации).

**Шаг 7. ChatAiService и ConversationAnalysisService.**

- Аналогично перейти на `build_safe_ai_client` или инкапсулировать логику конфигурации в один приватный метод, не дублируя в двух сервисах.

**Шаг 8. AI‑Task‑generator (`ai_tasks.py`).**

- Важно: сейчас он создаёт `AiClient()` напрямую.  
  Нужно:
  - либо использовать уже существующий `AiConfigService` + `SafeAiClient` по `clinic_id` (если таск работает по конкретным клиникам);
  - либо ввести отдельную политику:
    - использовать строго `allow_personal_data=False` для аналитики, если это cross‑clinic;
    - всё равно через `SafeAiClient`/`AiSanitizer`.

### 3.4. Наблюдаемость и валидация

**Шаг 9. Логирование и метрики.**

- Везде, где вводится/используется новый AI‑policy helper:
  - добавить структурированное логирование:
    - `clinic_id`, `provider_type`, `allow_personal_data`;
    - контекст вызова (orchestrator/chat_ai/analysis/ai_tasks).
- Проверить/дополнить метрики:
  - ошибки AI‑провайдера;
  - отключения/фоллбэки по политике.

**Шаг 10. Тестовые сценарии.**

- Юнит/интеграционные тесты для `AiConfigService`:
  - разные комбинации `ClinicAiSettings` (`ai_enabled`, `ai_provider_type`) → ожидаемые `allow_personal_data`.
- Тесты/песочница для `AiSanitizer`:
  - при `allow_personal_data=False` текст действительно очищается;
  - при `allow_personal_data=True` → pass‑through.

---

## 4. Dev‑чек‑лист для DEV_PROMPT_OMNI_POLICY_016

**Цель DEV:** реализовать описанную выше политику так, чтобы:
- ни один внешний AI‑вызов не обходил санитайзер/конфиг;
- разные типы провайдеров и режимы `allow_personal_data` работали как в BUSINESS_LOGIC_V2;
- изменения легко отследить и протестировать.

### Шаги для @DEV

1. **Создать helper для SafeAiClient (AI‑клиент фабрику).**
   - Новый модуль или функция:
     - `build_safe_ai_client(clinic_id: UUID, session: AsyncSession | None) -> SafeAiClient`.
   - Использовать внутри `AiConfigService` или рядом, чтобы не дублировать код.

2. **Обновить Omnichannel AI Orchestrator.**
   - Найти все места создания `AiClient`/`SafeAiClient` в `omnichannel_ai_orchestrator.py`.
   - Заменить их вызовом helper’а, передавая `clinic_id`.

3. **Обновить ChatAiService и ConversationAnalysisService.**
   - Заменить ручную сборку `AiClient` + `AiSanitizer` + `SafeAiClient` на использование helper’а (с учётом того, что иногда нет явного `clinic_id` — использовать `ctx.clinic_id` или безопасный дефолт по описанной политике).

4. **Привести AI‑Task‑generator к новой политике.**
   - В `ai_tasks.py`:
     - вместо `AiClient()` использовать `SafeAiClient` через helper;
     - определить, какой `clinic_id` или режим используется для аналитики;
     - убедиться, что при отсутствии конфигурации таск корректно заканчивается (no‑op).

5. **Убедиться, что все места конфигурации AI используют `AiConfigService`.**
   - Проверить по коду, что нет прямого чтения `ClinicAiSettings`/`settings.ai_*` для конфигурирования AI, минуя `AiConfigService`.

6. **Добавить/обновить тесты.**
   - Тесты на `AiConfigService` (разные `ClinicAiSettings` → `allow_personal_data`, `provider_type`).
   - Тесты на новый helper (`build_safe_ai_client`) — проверка, что:
     - при `allow_personal_data=False` текст маскируется;
     - при compliant/on_prem и `ai_enabled=True` — пропускается как есть.

7. **Проверить логи/метрики.**
   - Добавить логирование ключевых параметров политики при инициализации AI‑клиента.
   - Убедиться, что ошибки AI‑провайдера и fallback‑сценарии отмечаются в метриках (`omni_ai_provider_errors_total` и пр.).

