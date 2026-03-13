## DEV_PROMPT: AI‑оператор для чата и клиентов

> Архитектура и контекст: `ARCH_CHAT_AI_OPERATOR.md`, `ARCH_CHAT_PATIENT_ADMIN.md`, `BIZ_CHAT_MESSENGERS_AND_AI.md`, `ARCH_BUSINESS_TYPES_AND_LEXICON.md`.
> Цель: дать администратору и владельцу AI‑помощника в чате (резюме диалога, подсказки ответов, обзор по клиенту) **без автосендов**: AI только предлагает текст, человек всегда решает, что отправлять.

---

### Общие правила для @DEV

- Все вызовы AI проходят через backend:
  - **никаких API‑ключей на фронте**;
  - AI‑провайдер инкапсулирован в отдельном клиенте (`AiClient` или аналог).
- При любой ошибке AI:
  - API возвращает код `502/500` с безопасным сообщением;
  - frontend показывает «Не удалось получить подсказку» и продолжает работать как обычный чат.
- AI **никогда сам не отправляет сообщения клиенту**:
  - ответы приходят только как варианты текста;
  - админ выбирает вариант, может отредактировать и отправляет через уже существующий эндпоинт чата.
- Не логировать персональные данные в логах AI:
  - логируем только тип ошибки, идентификаторы (`clinic_id`, `conversation_id`, `patient_id`) и длительность запроса;
  - текст промптов/ответов не пишем в логи.

Рекомендуемый порядок: 1) конфиг и инфраструктура, 2) сервис ChatAiService, 3) admin‑API, 4) admin‑UI, 5) тесты.

---

### To‑dos (по шагам)

#### 1. Backend: конфигурация и клиент AI‑провайдера

1.1. **Расширить Settings и `.env.example`**

- В `src/core/config.py` добавить поля:
  - `ai_provider_base_url: str = ""`
  - `ai_provider_api_key: str = ""`
  - `ai_timeout_seconds: int = 10`
- В `.env.example` добавить переменные:
  - `AI_PROVIDER_BASE_URL=`
  - `AI_PROVIDER_API_KEY=`
  - `AI_TIMEOUT_SECONDS=10`
- Обновить инициализацию `Settings`, чтобы новые поля подтягивались из env.

1.2. **Инфраструктурный клиент AI (`AiClient`)**

- В `src/infrastructure/external_apis/` создать модуль, например `ai_client.py`:

```python
from typing import Any

import httpx

from src.core.config import settings


class AiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: int | None = None):
        self._base_url = base_url or settings.ai_provider_base_url
        self._api_key = api_key or settings.ai_provider_api_key
        self._timeout = timeout or settings.ai_timeout_seconds

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Конкретный формат зависит от провайдера; v1 — простой JSON POST.
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
```

- Детали формата (`/chat/completions` и структура payload) @DEV согласует с выбранным провайдером; важно, чтобы метод `complete` был единым входом для `ChatAiService`.

#### 2. Backend: DTO для AI‑ответов

2.1. **PatientAiInsight DTO**

- В `src/application/dto/chat_ai_dto.py` создать:

```python
from pydantic import BaseModel


class PatientAiInsight(BaseModel):
    summary: str
    risk_flags: list[str]
    next_best_action: str | None
```

2.2. **DTO для API‑ответов**

- В том же модуле:

```python
class ConversationSummaryResponse(BaseModel):
    summary: str


class SuggestReplyResponse(BaseModel):
    variants: list[str]
```

#### 3. Backend: сервис ChatAiService

3.1. **Реализация ChatAiService**

- В `src/application/services/chat_ai_service.py` реализовать сервис по `ARCH_CHAT_AI_OPERATOR.md`:

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.external_apis.ai_client import AiClient
from src.application.dto.chat_ai_dto import ConversationSummaryResponse, SuggestReplyResponse, PatientAiInsight


class ChatAiService:
    def __init__(self, session: AsyncSession, ai_client: AiClient | None = None):
        self.session = session
        self.ai_client = ai_client or AiClient()

    async def summarize_conversation(self, clinic_id: UUID, conversation_id: UUID) -> ConversationSummaryResponse:
        ...

    async def suggest_reply(
        self,
        clinic_id: UUID,
        conversation_id: UUID,
        admin_id: UUID | None,
        intent: str | None,
    ) -> SuggestReplyResponse:
        ...

    async def analyze_patient(self, clinic_id: UUID, patient_id: UUID) -> PatientAiInsight:
        ...
```

3.2. **Сбор контекста для `summarize_conversation`**

- Логика:
  - по `conversation_id` и `clinic_id` получить последние N сообщений (50–100) из `chat_messages`:
    - учитывать направление (`sender_type`), время, канал (internal/telegram/… если уже реализовано);
    - обрезать слишком длинные сообщения.
  - получить по `clinic_id`:
    - тип бизнеса и лексикон (`business_lexicon` из существующего сервиса/DTO клиники);
  - собрать промпт:
    - системная часть: роль AI (помощник администратора клиники, без мед. рекомендаций и обещаний, которых нет в системе);
    - пользовательская часть: лента сообщений в текстовом виде (формат диалога).
  - вызвать `AiClient.complete(...)` с нужным payload;
  - распарсить ответ в `ConversationSummaryResponse(summary=...)`.

3.3. **Сбор контекста для `suggest_reply`**

- Логика:
  - по `conversation_id` взять несколько последних сообщений (10–20, достаточно для контекста);
  - получить агрегаты по пациенту:
    - количество визитов, суммарная выручка, no‑show, наличие конфликтных флагов (при наличии соответствующих сервисов/репозиториев);
  - опциональное намерение:
    - строка `intent` («apologize», «invite», «info», …) может быть `None`;
  - сформировать промпт:
    - объяснить модели роль (админ стоматологии/клиники/салона);
    - передать выдержку диалога и краткий профиль клиента;
    - явно указать ограничения: вежливый тон, без мед. диагнозов, без обещаний скидок/услуг, которых нет.
  - вызвать `AiClient.complete(...)`;
  - из ответа получить 1–3 варианта коротких текстов, вернуть в `SuggestReplyResponse(variants=[...])`.

3.4. **Сбор контекста для `analyze_patient`**

- Логика:
  - по `patient_id` и `clinic_id` собрать:
    - визиты: количество, периодичность (интервал между визитами), последнюю дату;
    - финансовые показатели: суммарная выручка, средний чек;
    - количество отмен и no‑show;
    - наличие конфликтных флагов/жалоб;
  - при желании — выдержки из наиболее показательных сообщений (например, последние жалобы).
  - на основе этого построить промпт:
    - модель должна вернуть:
      - короткое резюме профиля клиента (2–4 предложения);
      - список рисков (ключевые слова/фразы);
      - предложение «что сделать сейчас» (next best action) в виде одной фразы.
  - вызвать `AiClient.complete(...)` и распарсить результат в `PatientAiInsight`.

3.5. **Обработка ошибок и таймаутов**

- Для всех методов:
  - обернуть вызовы `AiClient.complete` в `try/except httpx.HTTPError` и общие исключения;
  - логировать тип ошибки и идентификаторы (`clinic_id`, `conversation_id`, `patient_id`);
  - пробрасывать контролируемое исключение (например, `AiServiceError`) для маршрутизатора, чтобы он мог вернуть корректный HTTP‑код.

#### 4. Backend: admin‑API для AI‑оператора

4.1. **Эндпоинты в `admin_chat.py`**

- В `src/api/v1/routers/admin_chat.py` добавить:

```python
from src.application.dto.chat_ai_dto import ConversationSummaryResponse, SuggestReplyResponse, PatientAiInsight
from src.application.services.chat_ai_service import ChatAiService
```

- Эндпоинты:
  - `POST /api/v1/admin/chat/conversations/{conversation_id}/ai-summary`:
    - использует `clinic_id` из `get_default_clinic_id`;
    - создаёт `ChatAiService(session)` и вызывает `summarize_conversation`;
    - `response_model=ConversationSummaryResponse`.
  - `POST /api/v1/admin/chat/conversations/{conversation_id}/ai-suggest-reply`:
    - тело: `{ "intent": str | None }`;
    - использует `clinic_id` и текущего админа (можно передать `admin_id` в сервис для логов/тональности);
    - `response_model=SuggestReplyResponse`.

4.2. **Эндпоинт для AI‑обзора пациента**

- В отдельном или существующем admin‑роутере пациентов (например, `admin_client_reference.py` или новом `admin_patient_ai.py`) реализовать:
  - `GET /api/v1/admin/patients/{patient_id}/ai-insight`:
    - берёт `clinic_id` из `get_default_clinic_id`;
    - создаёт `ChatAiService(session)` и вызывает `analyze_patient`;
    - возвращает `PatientAiInsight`.

4.3. **Ошибки AI**

- При ошибке в `ChatAiService`:
  - возвращать HTTP‑код `502 Bad Gateway` или `500 Internal Server Error` с сообщением:
    - `"AI service temporarily unavailable"` (без деталей реализации).

#### 5. Frontend (admin‑UI): интеграция в чат и карточку клиента

5.1. **Типы и API‑клиент**

- В `frontend/src/api/types.ts` добавить:
  - `type ConversationSummary = { summary: string }`
  - `type SuggestReplyResult = { variants: string[] }`
  - `type PatientAiInsight = { summary: string; risk_flags: string[]; next_best_action?: string | null }`
- В `frontend/src/api/client.ts` (или аналогичном модуле):
  - методы:
    - `getConversationSummary(conversationId: string): Promise<ConversationSummary>`
    - `getSuggestReply(conversationId: string, intent?: string): Promise<SuggestReplyResult>`
    - `getPatientAiInsight(patientId: string): Promise<PatientAiInsight>`

5.2. **Кнопка «AI‑резюме» в чате**

- В компоненте admin‑чата:
  - добавить кнопку «AI‑резюме»:
    - при клике вызывает `getConversationSummary` для текущего `conversationId`;
    - показывает результат:
      - над лентой сообщений (например, collapsible блок);
      - или в боковой панели «Информация о диалоге».
  - При загрузке:
    - показывать спиннер/индикатор;
    - при ошибке — ненавязчивый алерт: «Не удалось получить AI‑резюме, попробуйте ещё раз».

5.3. **Кнопка «AI‑ответ» рядом с полем ввода**

- В форме ввода админского сообщения:
  - добавить иконку/кнопку «AI‑ответ»:
    - по клику:
      - опционально запрашивает у админа «намерение» (селектор: «Извиниться», «Пригласить», «Проинформировать», «Другое», «Без намерения»);
      - вызывает `getSuggestReply(conversationId, intent)`.
  - Показ вариантов:
    - 1–3 варианта в виде кликабельных чипов/кнопок под полем ввода;
    - по клику на вариант:
      - текст подставляется в поле ввода;
      - админ может его отредактировать и отправить обычным способом через существующий POST `/admin/chat/conversations/{id}/messages`.
  - При ошибке:
    - выводить текст вроде «Не удалось получить подсказку, напишите сами»;
    - не блокировать возможность ручного ввода.

5.4. **Блок «AI‑обзор» в карточке пациента**

- В admin‑карточке пациента:
  - добавить секцию «AI‑обзор»:
    - при первом открытии карточки:
      - либо загружать инсайт лениво по клику «Получить AI‑обзор»;
      - либо автоматически, но не блокируя остальной UI.
    - отображать:
      - `summary` — короткий текстовый блок;
      - `risk_flags` — список бейджей;
      - `next_best_action` — одну фразу «что сделать сейчас» (если есть).
  - Обновление:
    - кнопка «Обновить AI‑обзор» вызывает повторный запрос.

5.5. **UX‑ограничения и подсказки**

- В UI явно подсветить:
  - AI‑текст — это только подсказка; окончательное сообщение всегда проверяет человек.
- Не добавлять автоматических автосендов:
  - после выбора варианта AI‑ответа всегда требовать явного клика «Отправить».

#### 6. Тесты и проверка

6.1. **Backend**

- Unit/интеграционные тесты:
  - заглушка `AiClient` с предсказуемыми ответами;
  - проверка, что `summarize_conversation` и `suggest_reply` корректно собирают контекст и обрабатывают ответы;
  - проверка, что при ошибке провайдера поднимается контролируемое исключение, а роутер отдаёт 5xx.

6.2. **Frontend**

- Smoke‑проверки:
  - кнопка «AI‑резюме»:
    - при успехе — показывает текст;
    - при ошибке — не ломает чат.
  - кнопка «AI‑ответ»:
    - варианты подтягиваются и подставляются в поле ввода;
    - сообщение отправляется существующим путём.
  - блок «AI‑обзор»:
    - загружается и обновляется по запросу, не мешая другим действиям в карточке пациента.

---

### Завершение

После выполнения этого DEV_PROMPT:

- Админ в чате может:
  - получить краткое AI‑резюме диалога;
  - запросить варианты ответа и подставить их в поле ввода без автосендов.
- В карточке пациента доступен AI‑обзор с профилем, рисками и рекомендацией «что сделать сейчас».
- Вся логика AI изолирована в `ChatAiService` и `AiClient`, без API‑ключей на фронте и без влияния на основную работу чата при ошибках/таймаутах.

