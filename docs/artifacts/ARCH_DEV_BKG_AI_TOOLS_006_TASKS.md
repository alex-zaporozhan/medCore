## ARCH_DEV_BKG_AI_TOOLS_006_TASKS — сверх‑детализированные dev‑таски

> Связанная архитектура: `ARCH_DEV_BKG_AI_TOOLS_006.md`  
> Связанный DEV_PROMPT: `DEV_PROMPT_BKG_AI_TOOLS_006` (P2, BKG‑6, OMNI‑1/3)

---

### На потом — улучшения/укрепления (после v1)

7.1. **Единый маппинг ошибок Booking → AI‑tools (таблица/константы).**  
7.1.1. Вынести `error_code`/`error_message` для tools в один слой (например, `booking_ai_errors.py`), чтобы:  
      - `create/cancel/reschedule/get_slots` использовали один набор кодов;  
      - коды были стабильны для UI/Orchestrator/аналитики;  
      - ошибки `BookingService`/state‑машины приводились к доменному словарю (BKG_ERRORS_005).

7.2. **Adapter‑слой как отдельный модуль (не внутри tools).**  
7.2.1. Вынести преобразование DTO → вызовы `BookingService`/`ScheduleService` → DTO в `src/application/ai/booking_tools_adapter.py`:  
      - упростить сами tools (тонкий слой валидации + вызов адаптера);  
      - централизовать tokenization/clinic boundary/ошибки.

7.3. **RBAC через permissions (а не только roles).**  
7.3.1. Добавить `required_permissions` на tools (например `booking.ai_tools.use`, `booking.ai_tools.modify`) и привести к `ARCH_DEV_SEC_RBAC_022.md`.  
7.3.2. В `list_tools_for_context` проверять permissions как основной механизм, roles — как fallback.

7.4. **Лимиты и политика нагрузки для `get_available_slots`.**  
7.4.1. Сделать лимит диапазона конфигурируемым (per‑clinic/per‑channel).  
7.4.2. Добавить “hard cap” на количество возвращаемых слотов (например `max_slots`) + пагинацию/окна.  
7.4.3. (Опционально) Дать режим “suggest” (N лучших слотов), чтобы LLM не получал слишком большой ответ.

7.5. **Tasks/Attention для tool‑ошибок: пороги + дедуп + корректная модель.**  
7.5.1. Ввести дедупликацию по ключу `(clinic_id, tool_id, error_code, time_bucket)` и порог (N ошибок за M минут).  
7.5.2. Связывать Task не через `attention_kind="follow_up"` по умолчанию, а через отдельный `attention_kind`/тип/конвенцию (например `BOOKING_AI_TOOL_FAILURE`) либо отдельный механизм “системных” attention‑items.  
7.5.3. Хранить `source_event_id` (например `AiToolEvent.id`) для трассировки.

7.6. **Интеграционные тесты через `poetry` (целевое окружение) + CI‑профиль.**  
7.6.1. Добавить job/профиль, который поднимает Postgres/Redis и гоняет:  
      - `Omnichannel AI agent → get_available_slots → create_booking`;  
      - `… → cancel_booking`;  
      - негативные сценарии токенов/clinic boundary/permissions.  
7.6.2. Развести “DB‑free unit” и “DB integration” тесты по маркерам.

7.7. **Tokenization v2: не хранить UUID в токенах.**  
7.7.1. Перейти с `PATIENT#<uuid>` на псевдо‑ид (таблица маппинга) + TTL/rotation.  
7.7.2. Добавить аудит/метрики “token decode failures”.

### 1. Understand — текущее состояние Booking/Schedule и AI‑интеграций

1.1. **Инвентаризация методов `BookingService`/`ScheduleService`.**  
1.1.1. В `src/application/services/booking_service.py`, `schedule_service.py` и смежных файлах найти методы, которые:  
       - отдают свободные слоты (по клинике/доктору/услуге/периоду);  
       - создают записи (`create_booking`/аналоги);  
       - отменяют/переносят записи (`cancel_booking`, reschedule‑методы).  
1.1.2. Для каждого метода зафиксировать:  
       - набор параметров (наличие `clinic_id`, `patient_id`, `doctor_id`, `service_id`, временного интервала);  
       - используемые статусы `Booking` (enum/строки) и проверки state‑машины (`ARCH_DEV_BKG_STATE_002.md`);  
       - формат и типы ошибок (коды, исключения, тексты).

1.2. **Поиск существующих AI‑/tools‑интеграций вокруг Booking.**  
1.2.1. В `ai/tools_registry.py`, Omnichannel Orchestrator’е и связанных модулях найти:  
       - уже существующие tools, которые трогают Booking/Schedule (если есть);  
       - любые прямые обращения к `BookingService`/`ScheduleService` из AI‑слоя/Omnichannel.  
1.2.2. Зафиксировать, где сейчас:  
       - AI‑логика «подглядывает» в расписание;  
       - создаёт/отменяет записи без формализованного AI‑tools‑слоя.

1.3. **Инвентаризация multi‑clinic и BKG‑инвариантов.**  
1.3.1. По `ARCH_DEV_BKG_MULTI_003.md` и коду сервисов/роутеров выяснить:  
       - как именно сейчас применяется `clinic_id` при получении слотов и создании/отмене записей;  
       - где есть риск работы с «чужой» клиникой (особенно в admin/Omni‑контексте).  
1.3.2. Сопоставить это с RBAC (`ARCH_DEV_SEC_RBAC_022.md`) — какие роли сейчас могут выполнять операции записи и какие пермишены нужно будет требовать от Booking‑tools.

1.4. **Сопоставление с GAPS и ARCH_DEV Omnichannel/AI.**  
1.4.1. Открыть:  
       - `BACKEND_GAPS_Booking_NEXT.md` (BKG‑6);  
       - `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑1/3);  
       - `ARCH_DEV_OMNI_REGISTRY_015.md`, `ARCH_DEV_OMNI_POLICY_016.md`, `ARCH_DEV_AI_TOKENIZATION_025.md`.  
1.4.2. Зафиксировать, какие требования к Booking‑tools вытекают из этих документов:  
       - ограничения по ПД/tokenization;  
       - формат tools в registry;  
       - требования к логированию/OBS.

---

### 2. Design‑to‑code — DTO Booking‑tools и контракты handlers

2.1. **Уточнить список AI‑tools Booking v1.**  
2.1.1. На основе `ARCH_DEV_BKG_AI_TOOLS_006.md` и `ARCH_DEV_OMNI_REGISTRY_015.md` зафиксировать набор v1:  
       - `get_available_slots`;  
       - `create_booking`;  
       - `cancel_booking`;  
       - (опционально) `reschedule_booking` — если решено включить в v1.  
2.1.2. Для каждого tool описать:  
       - что он делает (одной фразой);  
       - какие инварианты должен уважать (статусы, clinic_id, права, ошибки).

2.2. **Спроектировать DTO для входа/выхода Booking‑tools.**  
2.2.1. В подходящем модуле (например, `src/application/dto/booking_ai_dto.py`) определить DTO:  
       - `GetAvailableSlotsInput/Output` (по эскизу из ARCH‑дока, расширив при необходимости);  
       - `CreateBookingInput/Output`;  
       - `CancelBookingInput/Output`;  
       - (если нужно) `RescheduleBookingInput/Output`.  
2.2.2. Учесть:  
       - обязательное поле `clinic_id`;  
       - использование токенов (`PATIENT#...`, `BOOKING#...`) вместо «голых» id для AI‑вызовов;  
       - отсутствие ПД в DTO при `allow_personal_data=False` (`ARCH_DEV_OMNI_POLICY_016`).

2.3. **Определить интерфейсы handlers для tools_registry.**  
2.3.1. На уровне application‑слоя/AI‑инфраструктуры описать сигнатуры handler’ов:  
       - каждый handler принимает `AiToolContext` + DTO входа;  
       - использует tokenization‑слой для маппинга токенов ↔ id;  
       - вызывает `BookingService`/`ScheduleService`;  
       - возвращает DTO выхода.  
2.3.2. Зафиксировать требования к `AiToolContext` (наличие `clinic_id`, ролей, `trace_id`) и то, как он будет формироваться Orchestrator’ом.

2.4. **Спроектировать mapping ошибок Booking → AI‑tools.**  
2.4.1. На основе `ARCH_DEV_BKG_ERRORS_005.md` описать таблицу сопоставлений:  
       - доменные коды ошибок (например, `SLOT_NOT_AVAILABLE`, `CLINIC_MISMATCH`, `INVALID_STATUS`);  
       - их отображение в `error_code`/`error_message` DTO tools;  
       - рекомендации/тексты для AI‑слоя (что можно подсказать пользователю).  
2.4.2. Зафиксировать эту таблицу либо в коде (константы), либо в документации около handler’ов.

---

### 3. Implement — Booking‑tools поверх `BookingService`/`ScheduleService`

3.1. **Реализовать DTO и adapter‑слой для Booking‑tools.**  
3.1.1. Создать модуль DTO из 2.2 и adapter‑функции, которые:  
       - принимают DTO входа;  
       - превращают их в вызовы соответствующих методов `BookingService`/`ScheduleService`;  
       - нормализуют ответы/исключения в DTO выхода.  
3.1.2. Особое внимание:  
       - корректная передача/проверка `clinic_id`;  
       - использование enum статусов Booking (`ARCH_DEV_BKG_STATE_002.md`);  
       - единообразная обработка ошибок.

3.2. **Реализовать handler `get_available_slots`.**  
3.2.1. В handler’е:  
       - принять `GetAvailableSlotsInput` + контекст;  
       - убедиться, что `clinic_id` в DTO и в контексте не конфликтуют;  
       - вызвать `ScheduleService.get_available_slots(...)` или эквивалент;  
       - сконвертировать результат в список `AvailableSlot` с минимально необходимыми полями.  
3.2.2. Добавить валидацию диапазонов дат/периодов (чтобы не допустить слишком тяжёлых запросов).

3.3. **Реализовать handler `create_booking`.**  
3.3.1. В handler’е:  
       - декодировать `patient_token` → `patient_id` через tokenization‑слой;  
       - использовать либо `slot_id`, либо комбинацию `doctor_id`+`service_id`+`date_time` (по согласованным правилам);  
       - вызвать `BookingService.create_booking(...)` и обработать результат:  
         - при успехе вернуть `booking_token`, статус, варнинги;  
         - при ошибках — заполнить `error_code`/`error_message` из маппинга 2.4.  
3.3.2. Убедиться, что создаваемая запись всегда принадлежит `clinic_id` из контекста/DTO и проходит статусы/валидации.

3.4. **Реализовать handler `cancel_booking` (и при необходимости `reschedule_booking`).**  
3.4.1. Для отмены:  
       - декодировать `booking_token` → `booking_id`;  
       - вызвать `BookingService.cancel_booking(...)` или state‑машину статусов;  
       - вернуть `CancelBookingOutput` с признаком успеха, новым статусом, кодом ошибки при неудаче.  
3.4.2. Для переноса (если реализуется в v1):  
       - определить явный контракт (какие поля можно менять, какие статусы допускают перенос);  
       - реализовать handler аналогично `create_booking`/`cancel_booking`, соблюдая инварианты.

---

### 4. Integrate — регистрация в tools_registry и Orchestrator

4.1. **Зарегистрировать Booking‑tools в `ai/tools_registry.py`.**  
4.1.1. Для каждого инструмента (`get_available_slots`, `create_booking`, `cancel_booking`, `reschedule_booking` при наличии):  
       - добавить запись с:  
         - `id`, `description`;  
         - `input_schema`, `output_schema` (ссылаясь на DTO);  
         - `required_permissions`/`allowed_roles` (например, `booking.ai_tools.use` для операторов).  
4.1.2. Убедиться, что registry учитывает `clinic_id` и RBAC из `ARCH_DEV_SEC_RBAC_022.md`.

4.2. **Интегрировать Booking‑tools в Orchestrator.**  
4.2.1. В Omnichannel Orchestrator’е (по `ARCH_DEV_OMNI_REGISTRY_015.md`):  
       - включить Booking‑tools в список доступных инструментов для AI‑агента в сценариях бронирования;  
       - обеспечить правильную передачу `AiToolContext` (clinic, роль, trace_id, токены пациента/записей).  
4.2.2. Определить и задокументировать, какие промпты/LLM‑шаблоны используют эти tools (на уровне Orchestrator’а, не в этом файле).

4.3. **Учесть влияние Omnichannel‑UI (`OMNI_UI_017`).**  
4.3.1. Согласовать с `ARCH_DEV_OMNI_UI_017_TASKS.md`, какие AI‑кнопки в UI будут завязаны на Booking‑tools (например, «Предложить слоты», «Создать запись», «Отменить запись»):  
       - убедиться, что они активируются только при доступности соответствующих tools и в допустимых статусах AI‑готовности (`stub`/`beta`/`prod`).  
4.3.2. Задокументировать ожидания по UX (например, необходимость явного подтверждения оператором перед созданием/отменой записи).

---

### 5. Observe — логи, метрики и Tasks/Attention для Booking‑tools

5.1. **Добавить логирование вокруг Booking‑tools.**  
5.1.1. В handlers и/или общем AI‑tools‑middleware логировать:  
       - `trace_id`, `tool_id`, `clinic_id`, тип действия (`get_slots`/`create`/`cancel`/`reschedule`);  
       - исход (успех/ошибка), `error_code` (если есть).  
5.1.2. Убедиться, что логи не содержат ПД (ФИО, телефоны) — только идентификаторы и агрегированные данные.

5.2. **Метрики по использованию и ошибкам Booking‑tools.**  
5.2.1. Ввести метрики:  
       - количество вызовов каждого инструмента по клиникам/ролям;  
       - доля успешных/ошибочных вызовов;  
       - время выполнения (особенно для `get_available_slots` и создания записей).  
5.2.2. Связать эти метрики с OBS‑цепочками из `ARCH_DEV_OBS_CHAINS_023.md` для цепей «Omnichannel → Booking».

5.3. **Attention/Tasks при аномалиях и неправильном использовании.**  
5.3.1. Определить критерии, когда Booking‑tools должны порождать Tasks/Attention (`ARCH_DEV_TASKS_MODEL_020.md`):  
       - частые отказы по причине некорректных параметров (ошибки интеграции);  
       - повторяющиеся ошибки при доступе к слотам/создании/отмене записей (потенциальные проблемы в Booking).  
5.3.2. Реализовать создание `AttentionItem`/Tasks с типами вроде `BOOKING_AI_TOOL_FAILURE`, с привязкой к `clinic_id` и контексту (тип операции, доменная сущность, если есть).

---

### 6. Stabilize — тесты, документация и связь с GAPS

6.1. **Покрыть Booking‑tools тестами.**  
6.1.1. Написать/обновить unit‑тесты для adapter‑слоя и handlers:  
       - позитивные сценарии: получение слотов, создание записи, отмена/перенос в допустимых статусах;  
       - негативные: недоступный слот, конфликт записей, некорректный `clinic_id`, ошибки прав.  
6.1.2. Проверить, что все ошибки корректно транслируются в `error_code` и не приводят к «тихой» потере контекста.

6.2. **Интеграционные тесты с Orchestrator/Omni.**  
6.2.1. Добавить базовые интеграционные тесты (или сценарии для QA) для цепочки:  
       - Omnichannel AI‑агент → вызов `get_available_slots` → выбор слота → вызов `create_booking`;  
       - Omnichannel AI‑агент → вызов `cancel_booking` по существующей записи.  
6.2.2. Убедиться, что при сбоях AI/Orchestrator’а (например, тайм‑ауты, ошибки tokenization) доменные данные Booking не повреждаются.

6.3. **Синхронизация GAPS и ARCH‑артефактов.**  
6.3.1. После завершения реализации обновить:  
       - `DEV_PROMPTS_NEXT.md` — статус `DEV_PROMPT_BKG_AI_TOOLS_006`;  
       - `BACKEND_GAPS_Booking_NEXT.md` (BKG‑6) — отметить закрытые/уточнённые пункты;  
       - при необходимости `BACKEND_GAPS_Omnichannel_NEXT.md` (OMNI‑1/3).  
6.3.2. При изменении архитектурных деталей по ходу реализации скорректировать соответствующие разделы `ARCH_DEV_BKG_AI_TOOLS_006.md` и, при необходимости, `ARCH_DEV_OMNI_REGISTRY_015.md`.

---

