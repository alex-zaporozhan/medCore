## ARCH_OMNICHANNEL_NEXT — домен Omnichannel & AI

### 1. Краткое описание домена

Omnichannel‑домен объединяет все каналы коммуникации (Telegram, WhatsApp, VK, Instagram, email, web‑чат, PWA‑чат) в один центр, поверх которого строится **AI‑уровень**:

- приём и нормализация входящих сообщений;
- хранение диалогов и контактов;
- настройка каналов и AI‑режимов;
- интеграция с CRM, Booking, Tasks/Attention.

### 2. Актуальная модель сущностей (по коду / BUSINESS_LOGIC_CURRENT/V2)

- `OmnichannelChat`, `OmnichannelMessage`, `OmnichannelContact`, `OmnichannelChannel`;
- `OmnichannelAiSettings`, `OmnichannelIntegrationConfig`;
- `Conversation`, `ConversationAiAnalysis`;
- `OmnichannelAuditLog` (аудит действий).

Роутеры:

- `integrations_gateway.py` — входящие webhooks мессенджеров/email/web‑чата;
- `patient_chat.py` — API для PWA‑чата;
- `admin_omni_chat.py`, `admin_ai_reports.py`, `admin_ai_settings.py`, `admin_ai_status.py`;
- owner‑уровень: `owner_omni_channels.py`, `owner_omni_ai_settings.py`, `owner_omni_audit.py`;
- AI‑агент: `ai_agent.py` (пока в статусе заглушки).

Frontend:

- PWA: `ChatPage.tsx`;
- Админка: `AdminOmniChatPage.tsx`, `AdminOmniChannelsPage.tsx`, `AdminOmniAiSettingsPage.tsx`, страницы AI‑отчётов.

### 3. Целевая модель vNext

1. **Явный AI‑слой с tools‑registry:**
   - отдельный модуль `ai_tools` / `tools_registry.py`:
     - описывает инструменты (`get_available_slots`, `create_booking`, `cancel_booking`, `get_price_list`, `get_patient_summary`, ...);
     - использует существующие доменные сервисы;
     - обеспечивает traceability (логирование, id запросов).
   - `OmnichannelAiOrchestrator` управляет function‑calling циклом (как в BUSINESS_LOGIC_V2).

2. **Единая модель диалога:**
   - все каналы приводятся к общему виду `Conversation` + `OmnichannelMessage`;
   - PWA‑чат пациента и внешний мессенджерский чат пациента связываются через `OmnichannelContact`.

3. **Интеграция с CRM/Booking/Tasks:**
   - новые контакты → создание `LeadCard`;
   - выявленные AI‑события (например, «клиент хочет записаться») → команды в Booking или CRM;
   - сложные кейсы/ошибки → задачи в `Task` / элементы AttentionFeed.

4. **Защита ПД и выбор AI‑провайдера:**
   - реализация политики из BUSINESS_LOGIC_V2 (AiSanitizer + ClinicAiSettings) как жёсткого инварианта;
   - различение режимов `external / ru_compliant / on_premise` с разными ограничениями по данным.

### 4. Связи с другими доменами

- **Booking:** AI‑инструменты для подбора слотов, создания/отмены записей.
- **CRM:** создание/движение лидов на основе коммуникаций.
- **Tasks & AttentionFeed:** генерация событий «что требует внимания» по перепискам и AI‑аналитике.
- **Marketing & Attribution:** использование каналов и source‑меток для сквозной аналитики.

