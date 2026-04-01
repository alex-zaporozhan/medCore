# DEV_PROMPTS_BACKEND_GAPS — Пошаговая реализация доработок бэкенда (один файл)

> **Назначение:** Единый промпт для @DEV: реализовать все изменения по выявленным недоработкам бэкенда (см. `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS_ARCH.md`). Выполнять шаги по порядку; после каждого — отмечать to-do.
>
> **Контекст:** Решения @LEAD/@ARCH внесены в `DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`; контракты и примечания обновлены. Этот документ — исполнительный чек-лист.

**Входы:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`, `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS_ARCH.md`.

---

## Как пользоваться

1. Выполняй **шаги по порядку** (G1 → G2 → … → G9).
2. Внутри шага — подпункты по порядку. После выполнения ставь галочку в **To-do**.
3. Контракты и пути — по `DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`. При расхождении с кодом — следовать артефакту.
4. Стандарты: `docs/ROLE_DEV.md` (ENTERPRISE QUALITY), tenant isolation, валидация, логирование.

---

# G1. NPS дашборда (документация / опциональность)

**Цель:** Зафиксировать поведение `nps_avg`: до появления модуля отзывов поле опционально и может быть всегда `null`.

**Шаги:**
1. Убедиться, что в `src/application/dto/reports_dto.py` поле `nps_avg` имеет тип `float | None = None`.
2. В `src/application/services/report_service.py` оставить текущее поведение (везде `nps_avg=None`), если расчёт NPS из отзывов не входит в текущий объём. Не добавлять расчёт без сущности отзывов.
3. (Опционально) В OpenAPI/описании эндпойнта dashboard-aggregate указать: «nps_avg — опционально; при отсутствии модуля отзывов всегда null; фронт не показывает виджет NPS при null».

**To-do G1**
- [x] DTO и report_service оставляют nps_avg опциональным; при необходимости обновлена документация эндпойнта.

**Критерий:** Ответ dashboard-aggregate содержит `nps_avg` (null или число); фронт при null не ломается.

---

# G2. Мини-лента сообщений по пациенту (GET patients/{id}/messages)

**Цель:** Эндпойнт для вкладки «Коммуникации» карточки пациента: последние сообщения диалога с этим пациентом.

**Файлы:** `src/api/v1/routers/admin_clinics_summary.py` или `admin_chat.py`, ChatService / репозиторий (patient → contact → conversation → messages).

**Шаги:**
1. Определить связь patient → contact (или conversation). Проверить существующие сущности: Patient, Contact, Conversation, Message; при необходимости маппинг по patient_id (например через Contact.patient_id или связующую таблицу).
2. Добавить в выбранный роутер эндпойнт:
   - `GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages`
   - Query: `limit: int = 20`, `cursor: str | None = None`.
   - ACL: clinic_id из path должен совпадать с current_admin.clinic_id; patient должен принадлежать клинике.
3. В сервисе (или в роутере): по patient_id найти conversation/contact; вызвать существующий метод получения сообщений (аналог list_messages_for_admin по conversation_id) с limit и cursor. Сформировать ответ `{ "items": [ MessageDto, ... ], "next_cursor": "..." | null }`.
4. При отсутствии диалога у пациента вернуть `items: []`, `next_cursor: null`. При patient not found или не своей клинике — 404.

**Контракт (из артефакта):**
```
GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages?limit=20&cursor=
Response 200: { "items": [ MessageDto, ... ], "next_cursor": "..." | null }
Response 404: patient not found or not in clinic
```

**To-do G2**
- [x] Эндпойнт GET .../patients/{patient_id}/messages добавлен.
- [x] Ответ в формате items + next_cursor; 404 при чужой клинике/несуществующем пациенте.
- [x] Роутер подключён в `src/api/v1/router.py` (если новый файл — не требуется при добавлении в admin_clinics_summary).

**Критерий:** Для пациента с диалогом возвращаются последние сообщения; без диалога — пустой items.

---

# G3. SubscriptionPackage: валидация kind (COUNT_BASED / BALANCE_BASED)

**Цель:** При создании/обновлении пакета проверять: COUNT_BASED → total_visits обязателен; BALANCE_BASED → total_amount обязателен. 422 при нарушении.

**Файлы:** `src/application/dto/loyalty_dto.py` (SubscriptionPackageCreate, SubscriptionPackageUpdate), `src/api/v1/routers/admin_loyalty.py`, при необходимости `src/application/services/loyalty_service.py`.

**Шаги:**
1. В DTO ограничить `kind` допустимыми значениями: `Literal["COUNT_BASED", "BALANCE_BASED"]` или валидатор Pydantic.
2. В роутере create_subscription_package (и при необходимости update): перед вызовом сервиса проверить — если kind == "COUNT_BASED", то total_visits должен быть задан и > 0; если kind == "BALANCE_BASED", то total_amount задан и > 0. Иначе raise HTTPException(422, detail с указанием поля).
3. Аналогичную проверку при необходимости перенести в LoyaltyService.create_package / update_package для единого места валидации.
4. Убедиться, что существующие миграции/модели SubscriptionPackage допускают значения kind COUNT_BASED и BALANCE_BASED (string 32 уже есть).

**To-do G3**
- [x] DTO: kind только COUNT_BASED | BALANCE_BASED.
- [x] Валидация при создании: COUNT_BASED → total_visits обязателен; BALANCE_BASED → total_amount обязателен; 422 при ошибке.
- [x] Валидация при обновлении (если меняется kind) — те же правила.

**Критерий:** POST с kind=COUNT_BASED без total_visits возвращает 422; с kind=BALANCE_BASED без total_amount — 422.

---

# G4. Напоминания о сгорании абонемента: реальная отправка

**Цель:** В задаче `check_expiring_packages` не только логировать, а отправлять напоминание клиенту через существующий канал (Notification или Omnichannel).

**Файлы:** `src/infrastructure/messaging/tasks/loyalty_tasks.py`, сервис уведомлений или omnichannel (send_with_fallback / создание Notification).

**Шаги:**
1. Определить, какой канал использовать: создание записи Notification (patient_id, clinic_id, channel=whatsapp/sms, template или body с текстом) с последующей отправкой через существующий воркер, либо вызов сервиса отправки в чат по contact/patient. Изучить `src/application/services/` и `src/domain/entities/notification.py` (или аналог).
2. В `_check_expiring_packages_async` после формирования сообщения `message` вместо только logger.info вызвать отправку: например создать Notification с payload или вызвать метод вида `notification_service.send_to_patient(patient_id, clinic_id, message)` / отправку в Omnichannel. Обработку ошибок обернуть в try/except; при неудаче логировать и не падать по всей задаче.
3. Параметр «N дней до сгорания» (сейчас EXPIRING_DAYS = 14) оставить константой или вынести в настройки клиники (опционально). Удалить или сократить TODO в коде про «would send».
4. Убедиться, что при отсутствии настроенного канала (WhatsApp/SMS) поведение задокументировано: заглушка (sent: false) допустима по артефакту; при невозможности отправить — только лог, без падения.

**To-do G4**
- [x] В check_expiring_packages после формирования текста вызывается отправка (Notification или канал).
- [x] Ошибки отправки обрабатываются (лог, без падения задачи).
- [x] TODO/заглушка «would send» убрана или заменена на реальный вызов.

**Критерий:** Запуск задачи по расписанию или вручную создаёт отправки/записи для пациентов с пакетами, сгорающими в течение N дней; при недоступности канала — только лог.

---

# G5. Owner Morning Brief и AI Supervisor Summary (Celery + Telegram)

**Цель:** Две Celery-задачи по расписанию: утренняя сводка и вечерний отчёт владельцу в Telegram.

**Файлы:** новый модуль `src/infrastructure/messaging/tasks/owner_integrations.py`, `src/infrastructure/messaging/celery_app.py`, при необходимости таблица настроек и эндпойнты GET/PATCH для настроек.

**Шаги:**

### 5.1. Задача Owner Morning Brief
1. Создать файл `src/infrastructure/messaging/tasks/owner_integrations.py`.
2. Реализовать задачу `send_owner_morning_brief(clinic_id: str)` (или с сигнатурой, подходящей для Celery): получить данные за вчера (касса/выручка, динамика), записи на сегодня, алерты (например остатки расходников). Использовать существующие ReportService, FinanceService, при необходимости репозитории. Сформировать текст сообщения (Markdown или plain text).
3. Получить telegram_chat_id владельца: из настроек клиники или из конфига/таблицы owner_integration_settings. Если настройки нет или рассылка выключена — выйти без ошибки.
4. Отправить сообщение в Telegram: вызов Bot API `sendMessage(chat_id, text)`. Токен бота — из настроек/конфига. При ошибке API — логировать, не падать.
5. Зарегистрировать задачу в `celery_app.py` (include модуля owner_integrations) и в beat_schedule: например `"owner-morning-brief": { "task": "owner_integrations.send_owner_morning_brief", "schedule": crontab(hour=9, minute=0) }` (или по времени UTC). Задача может итерировать по всем clinic_id с включённой настройкой и вызывать send для каждой.

### 5.2. Задача AI Supervisor Summary
1. В том же модуле реализовать `send_ai_supervisor_summary(clinic_id)`: агрегация за день — необработанные алерты из Attention Feed (или аналог), время реакции на сообщения, потерянная выручка (отмены, no-show). Сформировать текст отчёта.
2. Получить получателей (telegram_chat_id или список) из настроек; отправить в Telegram. Зарегистрировать в beat (вечернее время, например 20:00).
3. При отсутствии настроек или отключённой рассылке — не отправлять, не падать.

### 5.3. Настройки (опционально)
4. Если требуется UI в админке: добавить хранение (таблица или поля в clinic/settings): owner_morning_brief_enabled, owner_telegram_chat_id, morning_brief_send_at_utc; ai_supervisor_enabled, ai_supervisor_recipient_chat_ids, ai_supervisor_send_at_utc. Эндпойнты GET/PATCH `.../admin/clinics/{id}/settings/owner-brief` и `.../settings/ai-supervisor` по контракту из DEV_ARTIFACT_BACKEND_IMPLEMENTATION (B5.6). Если решено не делать UI — читать chat_id из конфига/env.

**To-do G5**
- [x] Модуль owner_integrations.py создан; задачи send_owner_morning_brief и send_ai_supervisor_summary реализованы.
- [x] Обе задачи зарегистрированы в Celery Beat с расписанием (09:00 и вечер).
- [x] Отправка в Telegram выполняется (Bot API); при отсутствии настроек/токена — тихий выход.
- [x] (Опционально) UI-настройки и эндпойнты для owner-brief и ai-supervisor добавлены (таблица owner_integration_settings, GET/PATCH .../settings/owner-brief и .../settings/ai-supervisor). При отсутствии настроек используется конфиг/env.

**Критерий:** По расписанию (или ручной вызов) утренняя и вечерняя задачи выполняются и отправляют сообщения в Telegram при настроенном chat_id.

---

# G6. Export Builder (Celery + хранилище + статус)

**Цель:** Реальная постановка экспорта в очередь Celery, генерация файла, сохранение в хранилище, выдача ссылки через статус.

**Файлы:** `src/api/v1/routers/admin_vault.py`, новый модуль задач например `src/infrastructure/messaging/tasks/export_tasks.py`, хранилище (локальная папка или S3 — по возможностям проекта).

**Шаги:**
1. Создать Celery-задачу `run_export(task_id, clinic_id, columns, format, entity_type, admin_id)`: по entity_type выбрать источник данных (patients, bookings, …), сформировать выборку по columns, сгенерировать файл (Excel/CSV). Сохранить файл в хранилище (например `exports/{task_id}.xlsx`) и записать в кеш/БД результат: task_id → status=completed, file_path или download_url. Лимит строк (например 10_000) и таймаут задачи — задать.
2. В `POST /admin/export`: сгенерировать task_id (UUID), поставить задачу `run_export.delay(task_id, ...)`, вернуть `{ task_id, status: "pending", message }`. clinic_id и admin_id брать из current_admin.
3. Добавить `GET /admin/export/status?task_id=...`: по task_id вернуть `{ task_id, status: "pending"|"completed"|"failed", download_url?: "...", error?: "..." }`. download_url — подписанная ссылка или путь к файлу (в зависимости от хранилища). При отсутствии task_id — 404.
4. Политика хранения: удалять файлы старше N дней (опционально, отдельная задача или при следующем экспорте).

**To-do G6**
- [x] Celery-задача run_export реализована; файл генерируется и сохраняется.
- [x] POST /admin/export ставит задачу и возвращает task_id.
- [x] GET /admin/export/status возвращает status и при готовности download_url.
- [x] Лимиты (строки, время) заданы и обрабатываются.

**Критерий:** Фронт может запросить экспорт, получить task_id, по статусу получить ссылку на скачивание.

---

# G7. Full Backup (Celery + статус + ссылка)

**Цель:** Реальная задача полного бэкапа, по готовности — ссылка (в ответе статуса или отправка в Telegram).

**Файлы:** `src/api/v1/routers/admin_vault.py`, новый модуль `src/infrastructure/messaging/tasks/backup_tasks.py`, хранилище для бэкапов.

**Шаги:**
1. Реализовать Celery-задачу `run_full_backup(task_id, clinic_id)`: дамп БД или выгрузка критичных данных в архив (SQL, JSON и т.д.), сохранение в хранилище. По готовности записать в состояние задачи: status=completed, download_url или отправить ссылку в Telegram (по контракту B5.5 — «ссылка в Telegram» допустима). При ошибке — status=failed, error в теле.
2. В `POST /admin/backup/request`: сгенерировать task_id, вызвать `run_full_backup.delay(task_id, clinic_id)`, вернуть `{ task_id, status: "pending" }`.
3. В `GET /admin/backup/status?task_id=...`: вернуть `{ task_id, status, download_url?: "..." }`. Состояние хранить в backend Celery (result) или в Redis/БД по task_id.
4. Ограничить одновременные бэкапы и время выполнения; при таймауте — status=failed.

**To-do G7**
- [x] Celery-задача run_full_backup создаёт бэкап и сохраняет в хранилище.
- [x] POST /admin/backup/request ставит задачу; GET /admin/backup/status возвращает status и при готовности download_url (или документирована отправка в Telegram).

**Критерий:** Запрос бэкапа ставит задачу; по статусу можно получить результат или ссылку.

---

# G8. Campaign ROI (агрегация воронки)

**Цель:** В `GET .../retention/campaigns/{campaign_id}/roi` возвращать реальные этапы воронки и paid_count вместо пустых значений.

**Файлы:** `src/api/v1/routers/admin_retention.py`, отчёты/репозитории по кампаниям, записям, платежам.

**Шаги:**
1. Определить источник данных для RecallCampaign: сколько отправлено (отправлено сообщений/рассылок), прочитано, перешли (клики), записались (bookings), оплатили в кассу (payments по этим записям). Использовать существующие сущности (RecallCampaign, рассылки, Booking, Payment) и связи.
2. В эндпойнте get_campaign_roi: загрузить кампанию по campaign_id и clinic_id; выполнить агрегации по этапам (отправлено → прочитано → перешли → записались → оплатили). Заполнить `CampaignRoiResponse.stages` списком `{ stage: string, count: int, conversion_pct?: float }` и `paid_count`.
3. При отсутствии данных по этапам возвращать пустые stages с нулями, но структуру сохранять. paid_count считать по оплаченным визитам, привязанным к кампании/источнику.

**To-do G8**
- [x] get_campaign_roi заполняет stages и paid_count из реальных данных.
- [x] Формат ответа соответствует CampaignRoiResponse (campaign_id, stages, paid_count).

**Критерий:** Для кампании с данными в ответе отображаются непустые этапы и paid_count.

---

# G9. Документация и контракты (финальная сверка)

**Цель:** Убедиться, что в артефактах отражены все принятые решения; контракт Attention claim уже зафиксирован в DEV_ARTIFACT_BACKEND_IMPLEMENTATION (B2.2); Revenue Saved by AI и nps_avg — с примечаниями.

**Шаги:**
1. Проверить, что в `DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`: B2.2 — фактический контракт PATCH .../items/claim с body; B2.1 — примечание про nps_avg optional; B5.3 — примечание про amount=null; B3.1.1 — контракт GET patients/{id}/messages; B6.4 — валидация kind. (Уже внесено @LEAD.)
2. В коде: описание эндпойнтов (docstring) при необходимости обновить под контракт (OpenAPI).
3. В `DEV_ARTIFACT_BACKEND_GAPS_ARCH.md` секцию «To-do для @ARCH» при необходимости отметить выполненными пункты, по которым решения приняты и реализованы.

**To-do G9**
- [x] Артефакты и код согласованы с контрактами; docstring/OpenAPI актуальны.

---

# Сводный To-do (все шаги)

| Шаг | Описание | Статус |
|-----|----------|--------|
| G1 | NPS: опциональность, документация | [x] |
| G2 | GET patients/{id}/messages (мини-лента) | [x] |
| G3 | SubscriptionPackage kind валидация | [x] |
| G4 | check_expiring_packages — реальная отправка | [x] |
| G5 | Owner Morning Brief + AI Supervisor (Celery + Telegram) | [x] |
| G6 | Export Builder (Celery + статус + ссылка) | [x] |
| G7 | Full Backup (Celery + статус + ссылка) | [x] |
| G8 | Campaign ROI — агрегация воронки | [x] |
| G9 | Документация и сверка контрактов | [x] |

**Критерий приёмки всех доработок:** Все to-do отмечены; контракты из DEV_ARTIFACT_BACKEND_IMPLEMENTATION соблюдены; новые эндпойнты и задачи работают по описанию.

**Примечания (реализовано по умолчанию):**
- Экспорты: путь из `EXPORT_STORAGE_PATH` (env) или `./data/exports`.
- Бэкапы: путь из `BACKUP_STORAGE_PATH` (env) или `./data/backups`.
- Telegram-брифы (G5): используется `telegram_owner_chat_id` (env) или fallback `telegram_admin_chat_id`; в конфиг добавлен `telegram_owner_chat_id`.
- Реализовано опционально: UI-настройки owner-brief/ai-supervisor (таблица owner_integration_settings, GET/PATCH .../settings/owner-brief и .../ai-supervisor); автоочистка старых экспортов/бэкапов (задача cleanup_old_exports_and_backups по расписанию 04:00 UTC).

---

# Ссылки

- **Контракты и фазы:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`
- **Исходный список недоработок:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_GAPS_ARCH.md`
- **Стандарты кода:** `docs/ROLE_DEV.md`, `docs/ROLE_ARCH.md`
