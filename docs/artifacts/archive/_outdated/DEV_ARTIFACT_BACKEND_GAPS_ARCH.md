# DEV_ARTIFACT_BACKEND_GAPS_ARCH — Недоработки бэкенда после фаз 0–5

> **Назначение:** Артефакт для @ARCH: перечень выявленных по коду дыр и недоработок бэкенда (соответствие контрактам DEV_ARTIFACT_BACKEND_IMPLEMENTATION и ожиданиям DEV_MASTER_PROMPT). @ARCH прописывает, как доработать; @DEV выполняет по указаниям.
>
> **Контекст:** Фазы 0–5 фронта помечены выполненными; проведена проверка бэкенда по контрактам B1–B6 и интеграциям.

**Входы:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`, `docs/DEV_MASTER_PROMPT.md`.

**Реализация доработок:** Пошаговый промпт с to-do для @DEV — **`docs/DEV_PROMPTS_BACKEND_GAPS.md`** (один файл на все изменения).

---

## Статус по фазам бэкенда (кратко)

| Фаза | Статус | Комментарий |
|------|--------|-------------|
| **B1** | ✅ Реализовано | Patient/Doctor summary, POST form/send-link |
| **B2** | ✅ Реализовано | Dashboard aggregate (new_leads, cancellations), Attention claim, suggest-slots, booking from waitlist |
| **B3** | ✅ Реализовано | Rich Patient/Booking/Doctor/Service card |
| **B4** | ✅ Реализовано | CRM stages aggregates, tasks source=ai + claim, POST transactions, checkout-info + use_subscription_id, marketing/insights |
| **B5** | ⚠️ Частично | search, ai/agent, revenue-saved-by-ai, retention, vault — есть; медиа/export/backup — заглушки; интеграции владельца — нет |
| **B6** | ⚠️ Частично | FamilyLink, liability, check_expiring_packages, Digital Pass — есть; отправка напоминаний о сгорании — заглушка |

---

## 1. Недоработки (для @ARCH: как доработать)

### 1.1. NPS в дашборде (B2 / отчёты)

**Где:** `src/application/dto/reports_dto.py` — поле `nps_avg` есть; `src/application/services/report_service.py` — везде передаётся `nps_avg=None`.

**Проблема:** Реальный расчёт NPS для виджета дашборда не реализован.

**Рекомендация @ARCH:** Либо ввести сущность отзывов/NPS и считать среднее по периоду (привязать к визитам/записям), либо явно зафиксировать в контракте, что `nps_avg` опционален и может быть всегда `null` до появления модуля отзывов. В последнем случае фронт не должен показывать виджет NPS при `null`.

---

### 1.2. Мини-лента переписки по пациенту (карточка Patient, вкладка Коммуникации)

**Где:** Карточка пациента (`GET .../patients/{patient_id}/card`) возвращает `comms` — только история уведомлений (Notification). В DEV_MASTER и техпаспорте: «при наличии API истории сообщений по контакту/пациенту — встроенная мини-лента последних сообщений» во вкладке Коммуникации.

**Проблема:** Эндпойнта «сообщения по patient_id / contact_id» для админки нет. Админ получает сообщения только по `conversation_id` (`GET .../conversations/{conversation_id}/messages`).

**Рекомендация @ARCH:** Ввести эндпойнт вида `GET /api/v1/admin/clinics/{clinic_id}/patients/{patient_id}/messages` (или `.../contacts/by-patient/{patient_id}/messages`) с лимитом и курсором, возвращающий последние сообщения диалога с этим пациентом (через привязку patient → contact → conversation). Контракт и точный путь зафиксировать в DEV_ARTIFACT_BACKEND_IMPLEMENTATION (B3 или отдельный подпункт). Фронт во вкладке «Коммуникации» при наличии ответа рисует мини-ленту; при отсутствии API — оставить только уведомления и кнопку «Открыть в чате».

---

### 1.3. Интеграции для владельца: Owner Morning Brief и AI Supervisor Summary

**Где:** В `src/infrastructure/messaging/celery_app.py` в beat только: reminders, run_ai_task_generator, check_expiring_packages. Задач `send_owner_morning_brief` и `send_ai_supervisor_summary` нет.

**Проблема:** По TECH_PASSPORT и DEV_MASTER (шаг 5.6) требуются утренняя сводка и вечерний отчёт владельцу в Telegram. Код не реализован.

**Рекомендация @ARCH:**  
- Добавить в Celery Beat две задачи (например в `src/infrastructure/messaging/tasks/owner_integrations.py`):  
  - `send_owner_morning_brief(clinic_id)` — 09:00, агрегаты (касса за вчера, записи на сегодня, алерты), отправка в Telegram.  
  - `send_ai_supervisor_summary(clinic_id)` — вечер, метрики (проигнорированные алерты, время реакции, потерянная выручка), отправка в Telegram.  
- Контракты настроек (время, вкл/выкл, `telegram_chat_id`) — по разделу «Интеграции для владельца» в DEV_ARTIFACT_BACKEND_IMPLEMENTATION. При необходимости добавить эндпойнты `GET/PATCH .../clinics/{id}/settings/owner-brief` и `.../ai-supervisor`.  
- Зафиксировать в артефакте зависимости (Telegram Bot API, наличие настроек по клинике).

---

### 1.4. Напоминания о сгорании абонемента (B6.3): отправка сообщений

**Где:** `src/infrastructure/messaging/tasks/loyalty_tasks.py` — задача `check_expiring_packages` выбирает подписи, формирует текст, но только логирует («would send»); нет вызова канала (WhatsApp/Omnichannel/Notification).

**Проблема:** Отправка напоминаний клиенту не выполняется.

**Рекомендация @ARCH:** Подключить отправку через существующий канал (Omnichannel/Notification/send_with_fallback): создание Notification с шаблоном или вызов сервиса отправки в чат пациента. Параметр «N дней до сгорания» (например 14) вынести в настройки клиники или оставить константой; зафиксировать в контракте. После реализации убрать заглушку (TODO в коде).

---

### 1.5. Omni-Vault: Export Builder и Full Backup (B5.5)

**Где:** `src/api/v1/routers/admin_vault.py` — `POST /admin/export` и `POST /admin/backup/request` возвращают `task_id` и сообщение «stub»; реальная постановка в Celery и генерация файла/ссылки не реализованы.

**Проблема:** Фронт не может получить готовый файл экспорта или ссылку на бэкап.

**Рекомендация @ARCH:**  
- **Export:** Celery-задача по body (columns, format, entity_type); после генерации файла — сохранение в хранилище (S3/локальное), возврат ссылки через `GET /admin/export/status?task_id=...` или callback; контракт в артефакте.  
- **Backup:** Celery-задача полного бэкапа; по готовности — ссылка (например в Telegram или download_url в статусе). Контракт уже описан в B5.5.  
- Указать лимиты (размер, время выполнения) и политику хранения файлов.

---

### 1.6. Retention: Campaign ROI (B5.4)

**Где:** `GET .../retention/campaigns/{campaign_id}/roi` в `admin_retention.py` возвращает `stages=[], paid_count=0`.

**Проблема:** Воронка ROI до «Оплатили в кассу» не считается.

**Рекомендация @ARCH:** Реализовать агрегацию по этапам кампании (Отправлено → Прочитано → Перешли → Записались → Оплатили в кассу) на основе существующих сущностей (RecallCampaign, рассылки, записи, платежи). Формат ответа — по контракту (CampaignRoiResponse со stages и paid_count). При отсутствии данных возвращать пустые этапы, но структуру соблюдать.

---

### 1.7. Attention Feed: расхождение контракта и реализации (B2.2)

**Где:** В DEV_ARTIFACT_BACKEND_IMPLEMENTATION описан вариант `PATCH .../attention-feed/items/{item_id}/claim`. В коде: `PATCH .../attention-feed/items/claim` с телом `{ "item_type": "task" | "follow_up", "item_id": "uuid" }`.

**Проблема:** Разный стиль API (item_id в path vs в body). Функционально claim реализован.

**Рекомендация @ARCH:** Зафиксировать в артефакте фактический контракт: `PATCH .../attention-feed/items/claim` с body `item_type`, `item_id`. Фронт уже под него завязан. Либо при необходимости унификации — добавить альтернативный путь `PATCH .../items/{item_id}/claim` с query `item_type` и помечать старый как deprecated.

---

### 1.8. SubscriptionPackage: kind COUNT_BASED / BALANCE_BASED (B6.4)

**Где:** В `subscription_package` есть поле `kind` (string); в лояльности используются `total_visits` / `total_amount`.

**Проблема:** В артефакте требуются явные значения COUNT_BASED / BALANCE_BASED и валидация при создании пакета.

**Рекомендация @ARCH:** Проверить допустимые значения `kind` в API создания/обновления пакета; при необходимости ограничить enum и валидировать: при kind=COUNT_BASED обязательны total_visits; при kind=BALANCE_BASED — total_amount. Документировать в контракте B6.4.

---

### 1.9. Revenue Saved by AI (B5.3)

**Где:** `GET .../reports/revenue-saved-by-ai` возвращает `amount=null` (заглушка).

**Проблема:** Виджет на дашборде не получает данных, пока нет Revenue Hunter / расчёта.

**Рекомендация @ARCH:** Оставить заглушку до появления расчёта или Celery-задачи Revenue Hunter; в контракте явно указать, что при отключённом функционале возвращается `amount: null`. Либо описать источник данных (таблица/кеш, заполняемая фоновой задачей) и формат для реализации.

---

## 2. Что уже в порядке (для справки)

- Patient/Doctor summary (B1), POST form/send-link (B1).  
- Dashboard aggregate: new_leads_count, cancellations_count (B2); nps_avg в DTO есть, расчёт — см. п. 1.1.  
- Attention Feed claim (B2); suggest-slots (B2); создание брони с waitlist_entry_id (B2).  
- Rich cards Patient, Booking, Doctor, Service (B3).  
- CRM stages с leads_count и sum_estimated_value (B4); tasks source=ai и claim (B4); POST finance/transactions (B4); checkout-info и complete с use_subscription_id (B4); marketing/insights (B4).  
- GET admin/search (B5); POST ai/agent (B5); retention segments и generate-offers (B5); GET .../media под retention (B5).  
- FamilyLink (B6); GET finance/liability (B6); check_expiring_packages в beat (B6); Digital Pass — patient loyalty /me с полями для карточек (B6).  
- Admin reports aggregate (dashboard-aggregate) и per-clinic dashboard с новыми полями.

---

## 3. To-do для @ARCH (сводка)

- [ ] **NPS:** Решить: расчёт из отзывов или явно optional в контракте (п. 1.1).  
- [ ] **Мини-лента по пациенту:** Ввести контракт и путь GET messages по patient_id для вкладки Коммуникации (п. 1.2).  
- [ ] **Owner Morning Brief и AI Supervisor:** Добавить Celery-задачи, beat, контракты настроек и Telegram (п. 1.3).  
- [ ] **Напоминания о сгорании:** Подключить отправку в check_expiring_packages (п. 1.4).  
- [ ] **Export и Backup:** Реализовать Celery + хранилище + контракт статуса/ссылки (п. 1.5).  
- [ ] **Campaign ROI:** Реализовать агрегацию воронки в get_campaign_roi (п. 1.6).  
- [ ] **Attention claim:** Зафиксировать фактический контракт (PATCH + body) в артефакте (п. 1.7).  
- [ ] **SubscriptionPackage kind:** Валидация COUNT_BASED/BALANCE_BASED в API (п. 1.8).  
- [ ] **Revenue Saved by AI:** Зафиксировать поведение при отключённом функционале или описать источник данных (п. 1.9).

---

## 4. Ссылки

- **Контракты бэкенда:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`  
- **Ожидания фронта:** `docs/DEV_MASTER_PROMPT.md`  
- **Роль @ARCH:** `docs/ROLE_ARCH.md`

---

*После того как @ARCH пропишет доработки (контракты, приоритеты), @DEV выполняет их по фазам B1–B6 и интеграциям; критерии приёмки — в DEV_ARTIFACT_BACKEND_IMPLEMENTATION.*
