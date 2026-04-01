## BACKEND_GAPS_Omnichannel_NEXT — домен Omnichannel & AI

### 1. Текущее состояние в коде

- **Сущности:** `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`, `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`, `Conversation`, `ConversationAiAnalysis`, `OmnichannelAuditLog`.
- **API:**
  - `integrations_gateway.py` — входящие webhooks;
  - `patient_chat.py` — API PWA‑чата;
  - `admin_omni_chat.py`, `admin_ai_reports.py`, `admin_ai_settings.py`, `admin_ai_status.py`;
  - `owner_omni_channels.py`, `owner_omni_ai_settings.py`, `owner_omni_audit.py`;
  - `ai_agent.py` — AI‑агент (stub).
- **Frontend:**
  - PWA `ChatPage.tsx`, админские страницы Omnichannel/AI.

### 2. Сравнение с ARCH_OMNICHANNEL_NEXT и BUSINESS_LOGIC_V2

- ARCH/V2 ожидают:
  - `ai_tools`/`tools_registry.py` с набором инструментов;
  - `OmnichannelAiOrchestrator` с полным циклом function‑calling;
  - жесткую политику работы с ПД и выбором AI‑провайдера.
- Фактическое состояние:
  - инфраструктура Omnichannel и AI‑аналитики реализована;
  - AI‑агент и tools‑registry пока заглушки.

### 3. Выявленные GAP’ы

- **OMNI-1 — отсутствие реализованного tools‑registry и Orchestrator (S1)**  
  - `ai_agent.py` и `useAiAgent.ts` возвращают статический ответ / заглушку;
  - нет слоя `ai_tools` в духе описания BUSINESS_LOGIC_V2.

- **OMNI-2 — политика работы с ПД может быть не полностью формализована (S2)**  
  - AiSanitizer и ClinicAiSettings упомянуты в бизнес‑логике, но требуют проверки реализации и жёсткой фиксации в коде.

- **OMNI-3 — неполная интеграция AI с CRM/Booking/Tasks (S2)**  
  - Omnichannel уже связан с CRM (переход в чат из Kanban), но двусторонняя AI‑интеграция (AI меняет стадии/создаёт записи/задачи) ещё не оформлена.

### 4. Оценка сложности исправления

- **OMNI-1:** средняя/высокая — нужно аккуратно добавить AI‑слой поверх существующих сервисов.
- **OMNI-2:** средняя — работа на стыке архитектуры, безопасности и интеграций.
- **OMNI-3:** средняя — потребует проектирования безопасных действий AI‑агента.

