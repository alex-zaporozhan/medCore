# Архитектура: Реализация AI‑подсистемы
> Базируется на `ARCH_AI_POLICY.md`. Документ для @ARCH → @DEV.

---

## 1. Схема данных

### 1.1. Таблица `clinic_ai_settings`

> Один набор настроек AI на клинику. Если multi‑clinic в одном инстансе — запись на каждую.

- `id UUID PK`
- `clinic_id UUID UNIQUE FK → clinics(id)`
- `ai_enabled BOOLEAN NOT NULL DEFAULT FALSE`
- `ai_mode TEXT NOT NULL DEFAULT 'draft_only'`
  - допустимые значения: `draft_only`, `safe_autoreply`, `analytics_only`
- `ai_business_prompt TEXT NULL`
- `ai_allowed_intents TEXT[] NOT NULL DEFAULT '{}'`
  - значения из контролируемого множества: `["schedule","location","faq","booking_change","price_info"]`
- `ai_autoreply_enabled BOOLEAN NOT NULL DEFAULT FALSE`
- `ai_autoreply_hours JSONB NULL`
  - структура: `{ "tz": "Europe/Moscow", "ranges": [ { "from": "22:00", "to": "08:00" } ] }`
- `ai_provider_type TEXT NOT NULL DEFAULT 'external'`
  - `external` | `on_prem` | `none`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Индексы:

- `ux_clinic_ai_settings_clinic_id UNIQUE (clinic_id)`

### 1.2. Таблица `conversation_ai_analysis`

> Для AI‑коуча и отчётов по конфликтам.

- `id UUID PK`
- `clinic_id UUID NOT NULL FK → clinics(id)`
- `conversation_id UUID NOT NULL FK → conversations(id)`
- `analysis_date DATE NOT NULL` (batched или per‑call)
- `sentiment TEXT NOT NULL` (`negative` | `neutral` | `positive`)
- `issue_category TEXT NOT NULL` (контролируемый справочник: `schedule`, `price`, `service`, `doctor`, `payment`, `other`)
- `is_conflict BOOLEAN NOT NULL`
- `is_resolved BOOLEAN NOT NULL`
- `admin_mistakes JSONB NOT NULL DEFAULT '[]'`
  - список строк.
- `business_root_causes JSONB NOT NULL DEFAULT '[]'`
- `suggested_playbook JSONB NOT NULL DEFAULT '[]'`
- `raw_ai_payload JSONB NULL`  — сырой ответ модели (для дебага, можно обрезать по размеру)
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

Индексы:

- `idx_conv_ai_analysis_clinic_date (clinic_id, analysis_date)`
- `idx_conv_ai_analysis_conv (conversation_id)`
- `idx_conv_ai_analysis_conflict (clinic_id, is_conflict, is_resolved)`

---

## 2. Backend: сервисы и слои

### 2.1. `AiSanitizer` и `SafeAiClient`

Файл: `src/core/ai_sanitizer.py`

```python
from dataclasses import dataclass
import re
from typing import Protocol


PHONE_RE = re.compile(r"(?:\+7|8)?\s?[\d\-\s()]{7,}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


@dataclass
class SanitizedText:
    original: str
    sanitized: str


class AiSanitizer:
    """Убирает/маскирует ПДн перед отправкой в AI."""

    def sanitize(self, text: str) -> SanitizedText:
        masked = PHONE_RE.sub("[PHONE]", text)
        masked = EMAIL_RE.sub("[EMAIL]", masked)
        # TODO: опционально добавить лёгкий NER/паттерны для ФИО
        return SanitizedText(original=text, sanitized=masked)
```

Файл: `src/infrastructure/external_apis/safe_ai_client.py`

```python
from typing import Any

from src.core.ai_sanitizer import AiSanitizer
from src.infrastructure.external_apis.ai_client import AiClient


class SafeAiClient:
    """Обёртка над AiClient с обязательной санитизацией текстов."""

    def __init__(self, ai_client: AiClient | None = None, sanitizer: AiSanitizer | None = None) -> None:
        self._client = ai_client or AiClient()
        self._sanitizer = sanitizer or AiSanitizer()

    def is_configured(self) -> bool:
        return self._client.is_configured()

    async def complete(self, payload: dict[str, Any], text_keys: list[str]) -> dict[str, Any]:
        """Санитизирует все значения по указанным ключам (messages[n].content и т.п.) и вызывает AiClient."""
        safe_payload = self._sanitize_payload(payload, text_keys)
        return await self._client.complete(safe_payload)

    def _sanitize_payload(self, payload: dict[str, Any], text_keys: list[str]) -> dict[str, Any]:
        # Реализация: обойти payload и для каждого ключа из text_keys применить self._sanitizer.sanitize(...)
        # Вернуть новую, безопасную копию payload.
        ...
```

`ChatAiService` и будущие AI‑сервисы должны использовать **только** `SafeAiClient`.

### 2.2. `ClinicAiSettingsService`

Файл: `src/application/services/clinic_ai_settings_service.py`

Задачи:

- CRUD для `clinic_ai_settings` (но без прямой работы с чувствительными полями провайдера — они остаются в `settings`/env).
- Валидация:
  - `ai_mode` ∈ допустимого множества;
  - `ai_allowed_intents` только из списка разрешённых;
  - `ai_autoreply_hours` имеет корректный формат (часы в 00:00–23:59).
- Метод `get_effective_prompt(clinic_id)`:
  - собирает:
    - глобальный базовый промпт (хардкод в модуле);
    - бизнес‑специфичный (на основе `clinic.business_type` и словарей лексики);
    - клиентский `ai_business_prompt`;
  - возвращает одну строку.

### 2.3. Расширение `ChatAiService`

- Перевод на `SafeAiClient`:
  - вместо `self.ai_client.complete(payload)` → `self.safe_ai_client.complete(payload, text_keys=[...])`.
  - `text_keys` указывают на поля `messages[].content` и т.п.
- Форматы ответов:
  - методы `summarize_conversation`, `suggest_reply`, `analyze_patient` должны:
    - формировать **prompts**, явно прося модель вернуть JSON‑структуру из `ARCH_AI_POLICY.md`;
    - парсить JSON (`json.loads`), валидировать по Pydantic‑модели;
    - в случае ошибок парсинга — логировать и возвращать fallback.

### 2.4. Новый сервис: `ConversationAnalysisService`

Файл: `src/application/services/conversation_analysis_service.py`

Задачи:

- Батч‑анализ диалогов (для отчётов и AI‑коуча):
  - принимает: `clinic_id`, `date_from`, `date_to`.
  - выбирает из `conversations` и `chat_messages` только релевантные (например, с негативной тональностью по ключевым словам или все за период).
  - готовит для каждого диалога краткий контекст (только последние N сообщений).
- Вызывает AI (через `SafeAiClient`) с промптом “проанализируй эти диалоги и верни JSON” (см. формат в `ARCH_AI_POLICY.md`).
- Сохраняет результаты в `conversation_ai_analysis`.

---

## 3. API‑контракты

### 3.1. Настройки AI для клиники

Роутер: `src/api/v1/routers/admin_ai_settings.py`  
Пример префикса: `/admin/clinics/{clinic_id}/ai-settings`

- `GET /admin/clinics/{clinic_id}/ai-settings`
  - Ответ:

```json
{
  "ai_enabled": true,
  "ai_mode": "draft_only",
  "ai_business_prompt": "строка от владельца",
  "ai_allowed_intents": ["schedule", "location"],
  "ai_autoreply_enabled": false,
  "ai_autoreply_hours": {
    "tz": "Europe/Moscow",
    "ranges": [{ "from": "22:00", "to": "08:00" }]
  },
  "ai_provider_type": "external"
}
```

- `PUT /admin/clinics/{clinic_id}/ai-settings`
  - Тело: та же структура, все поля опциональны для частичного обновления.
  - Ограничения:
    - нельзя менять `ai_provider_type` на уровне API без прав владельца (на будущее можно добавить RBAC).

### 3.2. AI‑коуч: отчёты по конфликтам

Роутер: `src/api/v1/routers/admin_ai_reports.py`  
Префикс: `/admin/ai-reports`

- `GET /admin/ai-reports/conflicts`
  - Параметры query:
    - `date_from`, `date_to` (обязательно)
    - `issue_category` (опционально)
    - `is_resolved` (опционально)
  - Ответ (агрегированный):

```json
{
  "summary": {
    "total": 12,
    "unresolved_conflicts": 3,
    "top_issue_categories": ["price", "schedule"]
  },
  "items": [
    {
      "conversation_id": "uuid",
      "sentiment": "negative",
      "issue_category": "price",
      "is_resolved": false,
      "admin_mistakes": ["обещал скидку", "не уточнил детали"],
      "business_root_causes": ["непрозрачный прайс"],
      "suggested_playbook": [
        "Переписать скрипт ответа на жалобы по цене"
      ],
      "created_at": "2026-03-03T12:00:00Z"
    }
  ]
}
```

- `POST /admin/ai-reports/conflicts/reanalyze`
  - Тело:

```json
{
  "date_from": "2026-03-01",
  "date_to": "2026-03-03"
}
```

  - Запускает повторный батч‑анализ (sync или async через Celery, на усмотрение @ARCH).

---

## 4. Frontend: страница конфигурации AI

### 4.1. Новая страница `AdminAiSettingsPage`

Файл: `frontend/src/admin/pages/AdminAiSettingsPage.tsx`

Функции:

- Отображать и редактировать:
  - `ai_enabled` (switch);
  - `ai_mode` (select: выключен/черновики/автоответ/аналитика);
  - `ai_business_prompt` (textarea с подсказкой шаблона);
  - `ai_allowed_intents` (multiselect);
  - `ai_autoreply_enabled` (switch) + `ai_autoreply_hours` (UI компонент для выбора диапазонов времени).
- Показывать статус подключения провайдера (данные с backend: “configured / not configured”, без ключей).

### 4.2. Интеграция с чат‑страницей и пациентами

- В `AdminChatPage`:
  - для режимов `draft_only` и `safe_autoreply` UI не меняется (пока).
  - на будущее можно добавить индикацию, когда сообщение было отправлено AI автоматически (по данным backend).
- В `AdminPatientsPage`:
  - `AI‑обзор` уже есть — фронту нужно только отразить новый формат (summary + flags + next_best_action) без изменений логики.

---

## 5. План для @DEV (high‑level)

Отдельный файл `DEV_PROMPTS_AI_MODULE.md` (см. рядом) должен разбить реализацию на фазы:

1. Внедрение `AiSanitizer` + `SafeAiClient` и перевод текущего `ChatAiService` на них.
2. Добавление `clinic_ai_settings` + CRUD‑сервис + API + страница настроек в админке.
3. Жёсткий JSON‑формат ответов AI для резюме диалогов, подсказок ответов и patient insight.
4. Реализация `ConversationAnalysisService` + таблицы `conversation_ai_analysis` + отчётов.

---

## 6. Failover‑поведение AI на уровне реализации

В дополнение к логике из `ARCH_CHAT_AI_OPERATOR.md` этот раздел задаёт технические требования к реализации отказоустойчивости.

### 6.1. Общий паттерн в `ChatAiService`

Для каждого публичного метода `ChatAiService` (`summarize_conversation`, `suggest_reply`, `analyze_patient`):

- перед обращением к внешнему AI:
  - проверять `self.safe_ai_client.is_configured()`;
  - при `False` сразу переходить к fallback‑ветке без вызова внешнего провайдера;
- оборачивать вызов `self.safe_ai_client.complete(...)` в `try/except` с таймаутом;
- при любой ошибке (таймаут, сетевое исключение, неверный формат JSON):
  - логировать ошибку с маскировкой ПД;
  - возвращать результат fallback‑ветки, соответствующий таблице в `ARCH_CHAT_AI_OPERATOR.md`.

### 6.2. Примеры fallback‑реализаций

- `summarize_conversation`:
  - взять последние N сообщений диалога (например, 10–20);
  - сформировать короткий текст вида:
    - "Последние сообщения:\n- ...\n- ...";
  - обрезать по максимальной длине (например, 500–800 символов);
  - вернуть как "упрощённое резюме".
- `suggest_reply`:
  - вернуть список из 0–2 заранее подготовленных шаблонов (общие вежливые ответы) без персонализации;
  - пример: "Спасибо за ваше сообщение, мы сейчас проверим информацию и вернёмся с ответом.".
- `analyze_patient`:
  - по агрегатам из БД (частота визитов, суммы, отмены) сформировать простой `PatientAiInsight` без сложного текста;
  - при невозможности — вернуть объект с пустыми/нейтральными полями.

### 6.3. Failover для батч‑анализа (`ConversationAnalysisService`)

В `ConversationAnalysisService`:

- при недоступности внешнего AI:
  - не создавать/обновлять записи `conversation_ai_analysis` для проблемных диалогов;
  - логировать факт пропуска с указанием `clinic_id`/диапазона дат;
  - не генерировать 5xx наружу: API должно возвращать "успех" с информацией о том, что анализ частично/полностью не выполнен (в зависимости от бизнес‑решения).

Эти правила обеспечивают соответствие реализации таблице failover‑сценариев и требованиям из `ARCH_HARDENING_ROADMAP.md`.
