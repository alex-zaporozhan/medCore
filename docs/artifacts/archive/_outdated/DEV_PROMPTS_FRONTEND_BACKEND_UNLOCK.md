# DEV_PROMPTS_FRONTEND_BACKEND_UNLOCK — Раскрытие бэкенда G1–G9 на фронте (один файл)

> **Назначение:** Единый промпт для @DEV: подключить фронт к уже реализованным доработкам бэкенда из `docs/DEV_PROMPTS_BACKEND_GAPS.md` (G1–G9). Выполнять шаги по порядку; после каждого — отмечать to-do. Запуск «от А до Б» из одного файла.
>
> **Контекст:** Бэкенд по G1–G9 реализован (NPS optional, GET patients/messages, валидация kind, check_expiring_packages, owner_integrations, export/backup Celery + статус, campaign ROI). Этот документ — исполнительный чек-лист фронта.

**Входы:** `docs/DEV_PROMPTS_BACKEND_GAPS.md`, `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`, `docs/DEV_MASTER_PROMPT.md`.

---

## Как пользоваться

1. Выполняй **шаги по порядку** (F1 → F2 → … → F6).
2. Внутри шага — подпункты по порядку. После выполнения ставь галочку в **To-do**.
3. Контракты и пути — по бэкенд-артефакту и фактическим роутерам (`admin_clinics_summary`, `admin_vault`, `admin_retention`, `admin_loyalty`).
4. Стандарты: `docs/ROLE_DEV.md`, отображение ошибок API (toast), EmptyState при пустых данных.

---

# F1. NPS дашборда (проверка)

**Цель:** Убедиться, что при `nps_avg === null` виджет NPS на дашборде не ломается и не показывается (или показывается как «Нет данных»).

**Шаги:**
1. В `frontend/src/admin/pages/AdminDashboardPage.tsx` (или где рендерятся метрики дашборда) проверить: данные для виджета NPS приходят из ответа dashboard-aggregate (`nps_avg: number | null`).
2. При `nps_avg == null` не показывать виджет NPS или показывать блок «NPS — нет данных» (по дизайну из TPF). Не обращаться к полю без проверки на null.
3. При необходимости обновить типы (DashboardReport / response type) так, чтобы `nps_avg` был `number | null`.

**To-do F1**
- [ ] Проверено: при nps_avg === null дашборд не падает; виджет NPS скрыт или с подписью «Нет данных».

**Критерий:** Ответ dashboard-aggregate с `nps_avg: null` не вызывает ошибок; виджет NPS при null не отображается или отображается нейтрально.

---

# F2. Мини-лента сообщений по пациенту (вкладка «Коммуникации»)

**Цель:** Во вкладке «Коммуникации» карточки пациента показывать мини-ленту последних сообщений с этим пациентом (без ухода из Drawer).

**Бэкенд-контракт (уже есть):**
```
GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages?limit=20&cursor=
Response 200: { "items": [ MessageDto, ... ], "next_cursor": "..." | null }
Response 404: patient not found or not in clinic
```

**Файлы:** `frontend/src/admin/components/entity/PatientEntityDrawer.tsx`, новый хук (например `frontend/src/hooks/useAdminPatientMessages.ts`) или вызов API в компоненте.

**Шаги:**
1. Добавить хук (или inline useQuery): запрос `GET /v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages` с параметрами `limit=20`, `cursor` (опционально). Включить запрос только при `activeTab === "comms"` и наличии `patient?.id` и `currentClinicId`.
2. В `PatientEntityDrawer` во вкладке «Коммуникации» (`Tabs.Panel value="comms"`): поверх существующего текста и кнопки «Открыть в чате» вывести список сообщений: автор, текст (или превью), дата. При пустом `items` — текст «Нет переписки» или оставить текущий текст.
3. При наличии `next_cursor` добавить кнопку «Ещё» / «Загрузить ещё», по клику запрашивать с `cursor=next_cursor` и дополнять список (или подменить query с новым cursor).
4. Ошибку 404 не показывать как общую ошибку страницы — во вкладке показать «Не удалось загрузить переписку» или пустой список.

**To-do F2**
- [ ] Хук/запрос GET .../patients/{patient_id}/messages добавлен; вызывается при открытой вкладке «Коммуникации».
- [ ] Во вкладке отображаются items (автор, текст/превью, дата); при пустом items — «Нет переписки».
- [ ] Поддержка next_cursor (кнопка «Загрузить ещё» или бесконечный скролл).

**Критерий:** Открытие карточки пациента → вкладка «Коммуникации» → видна мини-лента сообщений или «Нет переписки»; «Открыть в чате» по-прежнему ведёт в OmniChat.

---

# F3. SubscriptionPackage: форма с kind (COUNT_BASED / BALANCE_BASED)

**Цель:** Формы создания/редактирования пакета абонемента на фронте соответствуют бэкенд-валидации: при kind = COUNT_BASED обязателен total_visits; при BALANCE_BASED — total_amount. Показывать ошибки 422 по полям.

**Бэкенд:** Уже возвращает 422 с `detail` при нарушении (G3).

**Файлы:** Страница/форма пакетов лояльности (например `AdminLoyaltyPage` или отдельный Drawer/форма создания пакета), `frontend/src/hooks/useLoyalty.ts` (или аналог).

**Шаги:**
1. В форме пакета: поле «Тип» (kind) — выбор `COUNT_BASED` | `BALANCE_BASED` (Select или Radio). При `COUNT_BASED` — поле «Количество визитов» (total_visits) обязательно и > 0; при `BALANCE_BASED` — поле «Сумма» (total_amount) обязательно и > 0. Скрывать или дизейблить нерелевантное поле по выбранному kind.
2. Валидация на фронте перед отправкой: при COUNT_BASED проверять total_visits; при BALANCE_BASED — total_amount. При ошибке не вызывать API, показать ошибку под полем.
3. При ответе 422 от API показывать текст ошибки под формой или под соответствующим полем (из `detail` или полей ошибки валидации).

**To-do F3**
- [ ] В форме пакета: kind (COUNT_BASED/BALANCE_BASED), условные обязательные поля total_visits / total_amount.
- [ ] Фронт-валидация и отображение 422.

**Критерий:** Создание пакета с kind=COUNT_BASED без total_visits не уходит на сервер или сервер возвращает 422 и ошибка отображается; то же для BALANCE_BASED и total_amount.

---

# F4. Export Builder (POST → task_id → опрос статуса → скачивание)

**Цель:** Реальный поток экспорта: запрос экспорта → получение task_id → опрос статуса → при готовности — скачивание файла.

**Бэкенд-контракт (пути без clinic_id в path):**
```
POST /api/v1/admin/export
Body: { "columns": string[], "format": "excel" | "csv", "entity_type": "patients" | "bookings" | ... }
Response 200: { "task_id": string, "status": "pending", "message": "Export queued" }

GET /api/v1/admin/export/status?task_id={task_id}
Response 200: { "task_id": string, "status": "pending" | "completed" | "failed", "download_url": string | null, "error": string | null }
Response 404: task not found

GET /api/v1/admin/export/download/{task_id} — отдача файла (или использовать download_url из status, если бэкенд отдаёт полный URL).
```

**Файлы:** `frontend/src/admin/pages/AdminOmniVaultPage.tsx`.

**Шаги:**
1. Исправить вызовы API: **не использовать** `clinics/${clinicId}` в пути для export. Использовать:
   - `POST /v1/admin/export` с body `{ columns, format: "excel" | "csv", entity_type }`.
   - После успешного POST сохранять `task_id` в состоянии (useState или ref).
2. Запустить опрос: `GET /v1/admin/export/status?task_id=...` с интервалом (например 2 сек) пока `status === "pending"` или `status === "running"`. При `status === "completed"` — показать кнопку «Скачать»; при `status === "failed"` — показать ошибку из `error`.
3. Скачивание: если бэкенд отдаёт в status `download_url` как полный URL — использовать его; иначе формировать ссылку на `GET /v1/admin/export/download/{task_id}` (тот же origin + base path `/api`). Кнопка «Скачать» — открыть в новой вкладке или программно скачать файл (например через `<a href={...} download>` с учётом авторизации: возможно нужен fetch с токеном и создание blob URL).
4. Убрать TODO в `handleExportExcel` и `handleExportCsv`; реализовать вызов POST с выбранными `exportColumns`, `exportEntity` и выбранным форматом (Excel/CSV). Показывать во вкладке Export: после нажатия «Экспорт в Excel/CSV» — индикатор «Экспорт запущен…» и по готовности — «Скачать».

**To-do F4**
- [ ] POST /v1/admin/export вызывается с columns, format, entity_type; task_id сохраняется.
- [ ] Опрос GET /v1/admin/export/status?task_id= до completed/failed; при completed — кнопка «Скачать».
- [ ] Скачивание через download_url или GET /v1/admin/export/download/{task_id} (с учётом авторизации).

**Критерий:** Пользователь выбирает колонки и формат, нажимает экспорт → появляется прогресс → по готовности можно скачать файл.

---

# F5. Full Backup (POST → task_id → опрос статуса → скачивание)

**Цель:** Реальный поток бэкапа: запрос → task_id → опрос статуса по этому task_id → при готовности — скачивание или ссылка.

**Бэкенд-контракт (пути без clinic_id в path):**
```
POST /api/v1/admin/backup/request
Response 200: { "task_id": string, "status": "pending" }

GET /api/v1/admin/backup/status?task_id={task_id}
Response 200: { "task_id": string, "status": "pending" | "completed" | "failed", "download_url": string | null, "error": string | null }
Response 404: task not found

GET /api/v1/admin/backup/download/{task_id} — отдача файла.
```

**Файлы:** `frontend/src/admin/pages/AdminOmniVaultPage.tsx`.

**Шаги:**
1. Исправить URL: вызывать **не** `/v1/admin/clinics/${clinicId}/backup/request`, а `POST /v1/admin/backup/request` (без clinic_id в path; клиника из контекста токена на бэкенде).
2. После POST сохранять возвращённый `task_id` в состоянии (например `backupTaskId`). Опрос статуса вызывать с этим task_id: `GET /v1/admin/backup/status?task_id=${backupTaskId}` (не без task_id).
3. Реализовать опрос (polling) пока status pending/running; при completed показывать кнопку «Скачать» (download_url или GET /v1/admin/backup/download/{task_id}); при failed показывать error.
4. Убедиться, что useBackupStatus (или аналог) принимает task_id и запрашивает статус по нему; при отсутствии task_id не вызывать status (или показывать «Запросите бэкап»).

**To-do F5**
- [ ] POST /v1/admin/backup/request (без clinic_id в path); ответ task_id сохраняется.
- [ ] GET /v1/admin/backup/status?task_id= вызывается с сохранённым task_id; polling до completed/failed.
- [ ] При completed — кнопка «Скачать» (download или download_url).

**Критерий:** «Запросить бэкап» → после готовности можно скачать файл по ссылке/кнопке.

---

# F6. Campaign ROI (Retention): реальные этапы воронки и paid_count

**Цель:** На странице Retention (Waterfall и ROI) отображать реальные данные воронки по кампаниям: этапы (sent, read, clicked, booked, paid) и paid_count из API.

**Бэкенд-контракт:**
```
GET /api/v1/admin/clinics/{clinic_id}/retention/campaigns/{campaign_id}/roi
Response 200: { "campaign_id": "uuid", "stages": [ { "stage": string, "count": number, "conversion_pct": number | null }, ... ], "paid_count": number }
```

Списка кампаний с ROI одним запросом нет; список кампаний — из Recall:
```
GET /api/v1/admin/clinics/{clinic_id}/recall/campaigns
```

**Файлы:** `frontend/src/admin/pages/AdminRetentionPage.tsx`, при необходимости новый хук для ROI по кампании.

**Шаги:**
1. Получить список кампаний: использовать существующий или новый запрос к `GET /v1/admin/clinics/{clinic_id}/recall/campaigns` (если такой эндпойнт отдаёт список с id и названием). Если единого списка «retention campaigns» нет — использовать список recall-кампаний.
2. Для отображения таблицы ROI: для каждой кампании из списка вызывать `GET /v1/admin/clinics/{clinic_id}/retention/campaigns/{campaign_id}/roi`. Собрать массив { campaign_id, campaign_name, stages, paid_count }. При большом количестве кампаний — загружать ROI по одной при раскрытии строки или ограничить отображаемые (например первые 20).
3. В таблице «ROI кампаний» вывести колонки: Кампания, Отправлено (sent), Прочитано (read), Перешли (clicked), Записались (booked), Оплатили в кассу (paid). Значения брать из `stages` (по stage) и `paid_count`. При отсутствии данных по кампании — прочерки или 0.
4. Обработать 404 по campaign_id (кампания удалена или не своей клиники): в ячейке показать «—» или не показывать строку.

**To-do F6**
- [ ] Список кампаний для ROI: из GET .../recall/campaigns или аналог.
- [ ] Для отображаемых кампаний запрос GET .../retention/campaigns/{id}/roi; данные (stages, paid_count) выводятся в таблице.
- [ ] Таблица «ROI кампаний» заполняется реальными sent/read/clicked/booked/paid.

**Критерий:** На странице Retention во вкладке «Waterfall и ROI» таблица ROI показывает непустые этапы и paid_count для кампаний с данными.

---

# Сводный To-do (все шаги)

| Шаг | Описание | Статус |
|-----|----------|--------|
| F1 | NPS дашборд: при null не ломаться, виджет скрыт/«Нет данных» | [ ] |
| F2 | Мини-лента сообщений во вкладке «Коммуникации» карточки пациента | [ ] |
| F3 | Форма пакета: kind COUNT_BASED/BALANCE_BASED, валидация полей и 422 | [ ] |
| F4 | Export Builder: POST export → task_id → polling status → скачивание | [ ] |
| F5 | Full Backup: POST backup/request → task_id → polling status → скачивание | [ ] |
| F6 | Campaign ROI: список кампаний + GET roi по id, таблица stages и paid_count | [ ] |

**Критерий приёмки всех шагов:** Все to-do отмечены; контракты бэкенда G2, G3, G6, G7, G8 соблюдены на фронте; пользователь может пользоваться мини-лентой в карточке пациента, экспортом, бэкапом и таблицей ROI по кампаниям.

---

# Опционально (без обязательного to-do)

- **G5 (Owner Morning Brief / AI Supervisor):** Если в бэкенде есть эндпойнты настроек (GET/PATCH .../settings/owner-brief, .../settings/ai-supervisor), добавить в админке раздел/страницу настроек: вкл/выкл рассылки, chat_id, время отправки. При отсутствии эндпойнтов — поведение по конфигу/env на бэкенде, фронт не требуется.
- **G1 (NPS):** Если дашборд уже не показывает NPS при отсутствии данных — F1 сводится к быстрой проверке.

---

# Ссылки

- **Бэкенд-доработки (G1–G9):** `docs/DEV_PROMPTS_BACKEND_GAPS.md`
- **Контракты бэкенда:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`
- **Единый промпт фронта (фазы 0–6):** `docs/DEV_MASTER_PROMPT.md`
- **Стандарты кода:** `docs/ROLE_DEV.md`
