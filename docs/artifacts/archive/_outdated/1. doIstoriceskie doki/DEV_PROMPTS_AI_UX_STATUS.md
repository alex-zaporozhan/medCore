## DEV_PROMPTS — UX‑статусы AI и fallback

> Основание: `ARCH_CHAT_AI_OPERATOR.md`, `ARCH_AI_IMPLEMENTATION.md`, фактическая реализация фазы C (AI‑failover).
> Цель: поверх уже реализованного failover добавить прозрачные статусы AI и понятный UX для администратора, не ломая текущие контракты.

---

## 0. Режим работы @DEV/@FRONTEND

- Ничего не ломать в текущем поведении AI‑эндпоинтов (fallback уже реализован и проходит тесты).  
- Добавления должны быть **backward‑compatible**:
  - новые поля в DTO — только опциональные;
  - новые эндпоинты — без изменения существующих URL/методов.
- Работать по порядку задач ниже (backend → frontend).  
- После завершения:
  - прогнать существующие тесты `tests/api/test_pricing_and_ai.py`;
  - при необходимости добавить фронтовые UI‑тесты/скриншоты для новых статусов.

---

## 1. Backend — единый статус AI на уровне DTO

### 1.1 — Добавить поле `ai_status` в AI‑DTO (`chat_ai_dto.py`)

**Цель:** дать фронту признак, пришёл ли ответ от внешнего AI или из fallback‑логики.

- **Файл:** `src/application/dto/chat_ai_dto.py`
- **Действия:**
  - Для всех трёх DTO добавить опциональное строковое поле:
    - `ConversationSummaryResponse`: `ai_status: str | None = None`
    - `SuggestReplyResponse`: `ai_status: str | None = None`
    - `PatientAiInsight`: `ai_status: str | None = None`
  - Допустимые значения:
    - `"disabled"` — AI продуктово отключён (будущее расширение, пока можно не ставить);
    - `"fallback_local"` — ответ получен из локального heuristic‑алгоритма (fallback);
    - `"external_active"` — ответ пришёл от внешнего AI‑провайдера.

> Критерий: схемы OpenAPI обновились, но существующие клиенты без использования `ai_status` продолжают работать как раньше.

### 1.2 — Заполнение `ai_status` в `ChatAiService`

**Цель:** пометить, откуда именно пришёл ответ: снаружи или из fallback‑ветки.

- **Файл:** `src/application/services/chat_ai_service.py`
- **Действия (общий паттерн):**
  - Ввести маленький helper внутри класса:
    - например, `_base_ai_mode(self) -> str`, который возвращает:
      - `"external_active"`, если `self.ai_client.is_configured()` вернул `True`;
      - `"fallback_local"`, если `False` (на данном уровне можно не смотреть на `clinic_ai_settings`).
  - Для каждого публичного метода (`summarize_conversation`, `suggest_reply`, `analyze_patient`):
    - перед проверкой конфигурации зафиксировать `base_mode = self._base_ai_mode()`;
    - во всех местах, где используется **локальный heuristic‑fallback**:
      - выставлять `ai_status="fallback_local"` в возвращаемой DTO;
    - в успешном пути после вызова внешнего AI (`self.ai_client.complete(...)`) и успешного парсинга:
      - выставлять `ai_status=base_mode` (в текущей конфигурации это `"external_active"`).

> Критерий: для успешных вызовов с настроенным AI в ответах появляется `ai_status="external_active"`, для веток без провайдера и любых AI‑ошибок — `ai_status="fallback_local"`.

---

## 2. Backend — статус AI для отчётов по конфликтам

### 2.1 — Расширить `ConflictReportResponse`

**Цель:** дать фронту понять, что отчёты пустые из‑за отсутствия данных, а не из‑за неработающего AI.

- **Файл:** `src/api/v1/routers/admin_ai_reports.py`
- **Действия:**
  - В Pydantic‑модели `ConflictReportResponse` добавить поле:
    - `ai_status: str | None = None`
  - Значения использовать те же: `"disabled" | "fallback_local" | "external_active"`.

### 2.2 — Заполнение `ai_status` в `get_conflict_report`

**Цель:** различить «AI не запускался/отключён» и «AI работал, но конфликтов нет».

- **Файл:** `src/api/v1/routers/admin_ai_reports.py`
- **Действия:**
  - После выборки `rows` из `ConversationAiAnalysis`:
    - создать простой клиент: `safe_client = SafeAiClient(AiClient())`;
    - вычислить флаг `ai_configured = safe_client.is_configured()`.
  - Правила выставления `ai_status`:
    - если `rows` пусты и `ai_configured is False` → `ai_status="fallback_local"` (AI провайдера нет, анализ не выполняется);
    - если `rows` пусты и `ai_configured is True` → `ai_status="external_active"` (просто нет конфликтов в выбранном периоде);
    - если `rows` не пусты → `ai_status="external_active"`.
  - Вернуть `ConflictReportResponse(summary=..., items=..., ai_status=...)`.

> Критерий: фронт, глядя на пустой список `items`, может по `ai_status` показать разный текст: «конфликтов нет» vs «AI‑анализ сейчас недоступен».

---

## 3. Backend — единый metadata‑эндпоинт статуса AI (опционально, но желательно)

### 3.1 — Новый роутер `admin_ai_status`

**Цель:** дать фронту быстрый способ получить глобальный статус AI для клиники.

- **Файл:** `src/api/v1/routers/admin_ai_status.py` (новый)
- **Маршрут:**
  - `GET /api/v1/admin/ai-status`
- **Контракт (Pydantic‑модель):**
  - `AiStatusResponse`:
    - `ai_mode: str` — `"disabled" | "fallback_local" | "external_active"`;
    - `features: dict[str, bool]` — текущая доступность фич:
      - ключи: `"chat_summary"`, `"chat_suggest_reply"`, `"patient_insight"`, `"conflict_reports"`;
      - значения — пока `True` для всех, позже можно завязать на `clinic_ai_settings`.
- **Логика первой версии:**
  - `safe_client = SafeAiClient(AiClient())`;
  - если `safe_client.is_configured()` → `ai_mode="external_active"`;
  - иначе → `ai_mode="fallback_local"`;
  - `features` все `True`.

> Критерий: `GET /api/v1/admin/ai-status` возвращает валидный JSON без зависимости от внешнего AI, и его можно дёргать из админки без лишней нагрузки.

---

## 4. Frontend — единый слой статусов в hooks

### 4.1 — Нормализация ответа AI в hooks

**Цель:** чтобы страницы не парсили `ai_status` по‑разному, а работали через единый слой.

- **Файл:** `frontend/src/hooks/useChatAi.ts`
- **Действия:**
  - Ввести тип:
    - `type AiStatus = "unknown" | "disabled" | "fallback_local" | "external_active";`
  - Для хука `useConversationSummary`:
    - вернуть результат типа:
      - `{ data?: { summary: string; aiStatus: AiStatus }, ... }`
    - маппинг:
      - если `response.ai_status` есть → взять его;
      - если нет → `aiStatus="unknown"`.
  - Аналогично для `useSuggestReply`:
    - `{ data?: { variants: string[]; aiStatus: AiStatus }, ... }`.

> Критерий: компоненты UI в админке больше не лезут в «сырые» поля DTO, а используют `aiStatus` из хука.

---

## 5. Frontend — UX для AI‑кнопок и AI‑обзора

### 5.1 — `AdminChatPage`: статусы и сообщения

**Цель:** сделать поведение AI‑кнопок предсказуемым для администратора.

- **Файл:** `frontend/src/admin/pages/AdminChatPage.tsx`
- **Действия:**
  - Использовать `aiStatus` и `isPending` из `useConversationSummary` / `useSuggestReply`:
    - при `isPending` — показывать над лентой лёгкий индикатор «AI думает…» (`Text` + `Loader`).
    - при `aiStatus==="fallback_local"` — небольшой поясняющий текст рядом с кнопками:
      - «AI‑резюме и AI‑ответ сейчас работают в локальном режиме (без внешнего провайдера).»
    - при `aiStatus==="disabled"` (если появится такой режим) — текст:
      - «AI‑подсказки сейчас отключены администратором клиники.»
  - При ошибках запроса (mutation error, нет данных) — аккуратное уведомление:
    - «Не удалось получить ответ от внешнего AI, показан локальный вариант» **или** «Подсказка временно недоступна».

> Критерий: админ всегда понимает, работает ли внешний AI или только локальные подсказки, и не видит «немой тишины» при ошибках.

### 5.2 — Страница пациента: `ai-insight`

**Цель:** явно отличать внешний AI‑обзор от локального.

- **Файл:** страница пациента в админке (где показывается `PatientAiInsight`).
- **Действия:**
  - Отображать бейдж или подпись в блоке AI‑обзора:
    - `aiStatus==="external_active"` → «AI‑обзор (модель)»;
    - `aiStatus==="fallback_local"` → «AI‑обзор (локальный расчёт)»;
    - `aiStatus==="disabled" | "unknown"` → «AI‑обзор временно недоступен, основные данные по пациенту — ниже.»
  - При ошибке запроса (hook error) — явно выводить сообщение о временной недоступности AI без блокировки остальной карточки.

> Критерий: даже при полностью выключенном внешнем AI карточка пациента выглядит предсказуемо и информативно, без ощущения «сломалось всё».

### 5.3 — Страница отчётов по конфликтам

**Цель:** различать «нет данных» и «нет AI‑анализа».

- **Файл:** страница `AdminAiReports` (если уже есть; иначе создать минимальную).
- **Действия:**
  - Использовать поля:
    - `summary` (total, unresolved_conflicts, top_issue_categories);
    - `items`;
    - `ai_status`.
  - Логика:
    - если `items.length === 0` и `ai_status==="external_active"`:
      - текст: «За выбранный период конфликтов не найдено.»
    - если `items.length === 0` и `ai_status` в `"fallback_local" | "disabled"`:
      - текст: «AI‑анализ конфликтов сейчас недоступен. Вы можете продолжать работать с чатами и отчетами вручную.»
  - Над таблицей всегда показывать короткий summary по данным `summary`.

> Критерий: админ понимает, что пустой отчёт — это либо действительно отсутствие конфликтов, либо временная недоступность AI.

---

## 6. Frontend — индикатор статуса AI в админке

### 6.1 — `AdminAiSettingsPage`: глобальный статус

**Цель:** дать владельцу клиники очевидное понимание, как сейчас работает AI.

- **Файл:** `frontend/src/admin/pages/AdminAiSettingsPage.tsx`
- **Действия:**
  - Добавить запрос к `GET /api/v1/admin/ai-status`.
  - В шапке страницы отрисовать:
    - для `ai_mode="external_active"` — текст «AI подключён (внешний провайдер активен)»;
    - для `ai_mode="fallback_local"` — текст «AI в локальном режиме (подсказки без внешнего провайдера)»;
    - для `ai_mode="disabled"` (на будущее) — текст «AI отключён».
  - Под статусом — краткая легенда (1–2 предложения) о том, какие фичи доступны в каждом режиме.

> Критерий: владелец/админ, зайдя в настройки AI, за 1–2 секунды понимает, какое сейчас реальное состояние AI‑ассистента.

---

## 7. Выход для цепочки

- После внедрения:
  - все AI‑эндпоинты продолжают работать с существующими клиентами (нет breaking changes);
  - новые поля `ai_status` и эндпоинт `/admin/ai-status` позволяют фронту отображать:
    - состояние AI (внешний/локальный/выключен),
    - разницу между «нет данных» и «AI недоступен».
- @QA:
  - дополнить сценарии проверки AI‑fallback’ов (из `DEV_PROMPTS_QA_PRICING_AND_AI.md`) проверкой `ai_status` и новых UX‑текстов на ключевых экранах.

