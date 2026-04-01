# DEV_ARTIFACT_BACKEND_GAPS — Недостающие части бэкенда для DEV_MASTER_PROMPT и Loyalty Engine

> **Назначение:** Единый список того, чего **нет в коде бэкенда** и что требуется для полной сборки по `docs/DEV_MASTER_PROMPT.md` (строки 1–408) и для «Движка лояльности и капитала» (Loyalty & Wealth Engine) по сценарию ниже.  
> **Использование:** @ARCH структурирует этот список в отдельном артефакте и готовит промпт для @DEV по реализации недостающего бэкенда. Не создаём «песочные часы» — только полная сборка.

**Проверено по коду:** `src/api/v1/routers/*`, `src/application/services/*`, `src/domain/entities/*`, `src/infrastructure/**`.

---

## Часть 1. Пробелы по фазам DEV_MASTER_PROMPT

### Фаза 1 — Универсальные законы

| № | Требование | Статус в коде | Что добавить |
|---|------------|----------------|--------------|
| 1.1 | Zero-Click Context: данные для HoverCard по пациенту/врачу (телефон, LTV, след. визит) | Нет лёгкого эндпойнта | `GET /api/v1/admin/patients/{id}/summary` и/или `GET /api/v1/admin/doctors/{id}/summary` (или вложенные поля в списках) — минимальный DTO для тултипа без полной загрузки карточки. |
| 1.2 | Отправка формы по ссылке из контекста пациента/записи | Нет | `POST /api/v1/admin/forms/send-link` (или `form/send-link`): body `patient_id` или `booking_id`, `template_id`; ответ: уникальный URL + опционально вызов отправки в WhatsApp/SMS. Контракт зафиксировать. |

### Фаза 2 — Ключевые экраны

| № | Требование | Статус в коде | Что добавить |
|---|------------|----------------|--------------|
| 2.1 | Dashboard: 4 метрики (записи сегодня, выручка, новые лиды, NPS/отмены) | Есть `dashboard-aggregate` с bookings_*, new_patients, revenue. Нет «новые лиды», нет отдельно NPS/отмены | Расширить DTO/сервис: метрика «новые лиды» за период, метрика отмен (и при возможности NPS). Либо отдельные эндпойнты под виджеты. |
| 2.2 | Attention Feed: действие «Взять в работу» (claim) | Есть GET feed, POST close follow-up. Нет универсального claim задачи из Feed | `PATCH /api/v1/admin/clinics/{clinic_id}/attention-feed/{item_id}/claim` или аналог: назначение задачи на текущего админа, перенос в My Focus. Либо единый контракт «claim по типу элемента» (task_id, message_id и т.д.). |
| 2.3 | Расписание: подсказка «идеальных» слотов при создании записи | Нет | `GET /api/v1/admin/clinics/{clinic_id}/schedule/suggest-slots` (или в составе schedule): параметры doctor_id, date, service_id?; возврат слотов с учётом «дыр» (опционально бэкенд-алгоритм). |
| 2.4 | Создание записи из листа ожидания (Waitlist → слот) | Есть CRUD waitlist. Нет создания брони «из» записи листа | `POST /api/v1/admin/bookings` (или отдельный endpoint) с опциональным `waitlist_entry_id`: создание брони с привязкой к пациенту/услуге из листа, пометка/удаление записи листа. |
| 2.5 | Формы: отправка ссылки на форму (см. 1.2) | — | См. пункт 1.2. |

### Фаза 3 — Глубина сущностей

| № | Требование | Статус в коде | Что добавить |
|---|------------|----------------|--------------|
| 3.1 | Карточки Patient, Booking, Doctor, Service: полные данные по вкладкам в одном или минимальном числе запросов | Обычно отдельные GET по id и отдельные списки (bookings, payments и т.д.) | Либо расширить GET patient/{id}, booking/{id}, doctor/{id}, service/{id} вложенными коллекциями (bookings, payments, notes, consumables, service_doctor, working_hours и т.д.), либо явные эндпойнты вида GET patient/{id}/visits, GET patient/{id}/finances — по контракту TPF_MODULE_ENTITIES. |

### Фаза 4 — CRM, задачи, финансы

| № | Требование | Статус в коде | Что добавить |
|---|------------|----------------|--------------|
| 4.1 | CRM Kanban: в шапке столбца сумма бюджетов (например «Думают (5) — 150 000 ₽») | LeadCard имеет estimated_value. В ответах list/stages сумм по этапам нет | В ответ `GET /admin/crm/stages` (или list leads) добавить агрегат: по каждому stage_id — sum(estimated_value), count. Либо отдельный `GET /admin/crm/stages/aggregates`. |
| 4.2 | Задачи: фильтр «Задачи от AI», действие «Принять в работу» | Есть list, create, update. В Task есть source (manual|ai_suggested|…). Нет фильтра source=ai в API, нет отдельного «claim» | В `GET /admin/tasks` добавить query `source=ai`. Добавить `POST /admin/tasks/{id}/claim` (назначение на текущего пользователя) для AI-пула. |
| 4.3 | Финансы: ручные операции Внести / Изъять / Перевод | Есть list_cashboxes, list_financial_transactions. Нет POST создания транзакции из UI | `POST /api/v1/admin/clinics/{clinic_id}/finance/transactions`: body cashbox_id, amount, type (income|expense|transfer), category; для transfer — from_cashbox_id, to_cashbox_id. Валидация обязательных полей (Relational Integrity). |
| 4.4 | Аналитика: AI Marketing Advisor (текстовые инсайты) | Есть отчёты, воронка, attribution. Нет блока с инсайтами от AI | При наличии AI: `POST /api/v1/ai/marketing-insights` или `GET /api/v1/admin/clinics/{id}/marketing/insights` — возврат текстовых рекомендаций по данным UTM/воронки. Контракт зафиксировать. |

### Фаза 5 — Дифференциаторы

| № | Требование | Статус в коде | Что добавить |
|---|------------|----------------|--------------|
| 5.1 | Spotlight: глобальный поиск по разделам + пациентам/записям | Нет единого эндпойнта | `GET /api/v1/admin/search?q=...` (или под роутером admin): возврат секций (навигация) + пациенты (id, name, phone) + записи (id, patient, date) по текущей клинике. Ограничение лимита и прав. |
| 5.2 | Spotlight: вкладка «Спросить AI» (AI Command Line) | Есть function-calling в omnichannel. Нет отдельного эндпойнта для произвольного запроса из Spotlight | `POST /api/v1/ai/agent` (или `/api/v1/admin/ai/command`): body text; вызов AI-агента с function-calling; возврат ответа. Rate limit, очередь при необходимости. |
| 5.3 | Виджет «Спасённая выручка (AI)» на Dashboard | Нет | Эндпойнт или поле в dashboard-aggregate: «выручка, спасённая ИИ за ночь» (из Celery/фонового процесса Revenue Hunter). Отдавать только при включённом Revenue Hunter. |
| 5.4 | Retention: AI-сегменты, генерация офферов, ROI кампании | Есть recall (кампании, сегменты). Нет AI-сегментов и AI generate-offers, нет воронки ROI до кассы в одном контракте | По артефакту F5_RETENTION: API сегментов (в т.ч. AI), `POST ai/generate-offers`, статистика кампании (воронка до «Оплатили в кассу»). |
| 5.5 | Omni-Vault: медиа-галерея, Data Export Builder, Full Backup | Нет | Медиа: `GET /api/v1/admin/media` (полиморфная привязка к patient/booking/message), фильтры по типу/дате. Export Builder: `POST /api/v1/admin/export` (columns, format=excel|csv), превью/файл. Full Backup: запуск задачи (Celery), `GET .../backup/status`, ссылка на скачивание (например в Telegram). |
| 5.6 | Owner Morning Brief / AI Supervisor Summary | Нет в API | Бэкенд/Celery: генерация отчётов и отправка в Telegram. Конфиг в настройках. Для UI не обязателен отдельный эндпойнт; при наличии — статус «последняя отправка». |

---

## Часть 2. Движок лояльности и капитала (Loyalty & Wealth Engine) — требования от Gemini

Сценарий не «просто цифра 10→9», а уровень топовых фитнес-приложений и премиум-клиник.

### 2.1. Цитируемый сценарий (сохранить для @ARCH, без потери деталей)

> Обычный абонемент в старой CRM — это просто цифра (было 10, стало 9). Мы создаём «Движок Лояльности и Капитала» (Loyalty & Wealth Engine).

- **Apple Wallet Aesthetics:** В PWA абонемент — как красивая карта (NFC-чип визуально), прогресс-бар, срок действия. Кнопка на карте «Записаться по абонементу» → мастер записи с отфильтрованными услугами пакета; на этапе чекаута — «Оплачено абонементом».
- **Family Sharing (Family Pass):** Депозит/пакет привязывается к нескольким пациентам (муж — владелец, жена и ребёнок — привязанные); все списывают с одного пакета.
- **Auto-Checkout (Zero-Click оплата):** При завершении визита система сама определяет, что у клиента есть пакет на эту услугу. В Checkout Hub админ видит галочку «Списать 1 визит с абонема» без ручного поиска.
- **AI-угроза сгорания (The Fear of Loss):** За N дней до сгорания абонемента ИИ пишет клиенту (WhatsApp и т.д.): «У вас сгорят 2 массажа через 2 недели! Давайте найдём окно?» — возврат в клинику и допродажи.

### 2.2. Дополнение в BUSINESS_LOGIC_V2 (домен Loyalty & Packages)

- **Типы пакетов:** `COUNT-BASED` (например 10 массажей), `BALANCE-BASED` (депозит 100 000 ₽ на любые услуги).
- **Сущности (маппинг на текущий код):**
  - `PackageTemplate` → уже есть как **SubscriptionPackage** (шаблон: название, тип, цена, ценность, срок, список услуг).
  - `PatientPackage` → уже есть как **CustomerSubscription** (купленный абонемент; состояния: active, frozen, expired, exhausted).
  - `PackageTransaction` → уже есть как **SubscriptionUsage** (история списаний: дата, услуга, врач, кто списал).
  - **FamilyLink** — **отсутствует:** связь Many-to-Many между пакетом (CustomerSubscription) и другими Patient (члены семьи), чтобы они могли тратить с одного пакета.
- **Интеграция с ERP:** Оплата абонемента — в кассу как аванс (обязательство). При списании визита — виртуальное распределение на ЗП врачу (SalaryTransaction).
- **AI-триггеры:** Celery-задача `check_expiring_packages`: пакеты, истекающие через 14 дней → передача в AiClient для персонализированных напоминаний (WhatsApp и т.д.).

### 2.3. Недостающее в бэкенде по Loyalty Engine

| № | Элемент | Статус | Что сделать |
|---|---------|--------|-------------|
| L1 | **FamilyLink** (семейный шеринг) | Нет сущности и API | Модель: связь CustomerSubscription ↔ Patient (многие ко многим — «кому разрешено тратить»). API: в Drawer пациента-владельца «+ Добавить члена семьи» (поиск пациента); привязанный пациент видит в PWA тот же пакет с пометкой «Доступ: Иван И.». |
| L2 | **Auto-Checkout (Smart Detection)** | В коде есть `select_subscription_for_booking` и `use_subscription_for_booking` при complete_booking | Для Checkout Hub в UI нужен контракт: при открытии чекаута (или при GET booking/{id}/checkout-info) возвращать список подходящих активных пакетов (package_id, name, remaining_visits/amount), чтобы фронт показал галочку «Списать с абонемента X». Если сейчас выбор пакета не передаётся явно — добавить в `complete_booking` опциональный параметр `use_subscription_id` и вызывать `use_subscription_for_booking` только при его наличии. |
| L3 | **Дашборд обязательств (Liability Dashboard)** | Нет | «Деньги в воздухе» (Unearned Revenue): сумма, которую клиенты заплатили за абонементы, но ещё не отходили. Эндпойнт для владельца: например `GET /admin/clinics/{id}/finance/liability` или блок в отчёте. Агрегат: сумма остатков по активным CustomerSubscription (remaining_visits * условная цена или remaining_amount). |
| L4 | **AI check_expiring_packages** | Нет | Celery-задача: выбор пакетов с expires_at через 14 дней (или конфигурируемо), вызов AiClient/интеграции для отправки напоминания в WhatsApp (и др. каналы). Контракт с Omnichannel и шаблонами сообщений. |
| L5 | **Типы пакетов COUNT-BASED / BALANCE-BASED** | В SubscriptionPackage есть `kind`: visits \| balance \| mixed | Привести наименования и логику к COUNT-BASED / BALANCE-BASED по тексту Gemini; при необходимости расширить миграции и валидацию. |
| L6 | **PWA: Digital Pass (карточка абонемента)** | Есть patient_loyalty (список абонементов пациента) | Убедиться, что API отдаёт всё нужное для карточки: название, прогресс (remaining/total), дата сгорания, список услуг пакета — для кнопки «Записаться по абонементу» (мастер записи с фильтром по услугам пакета). |

---

## Часть 3. Сводная таблица: что есть / чего нет

| Блок | Есть в коде | Нет / неполно |
|------|-------------|----------------|
| Фаза 0 | — | Нового API не требуется |
| Фаза 1 | CRUD сущностей, ActionMenu-эндпойнты по разным модулям | Patient/Doctor summary для HoverCard; POST form/send-link |
| Фаза 2 | Dashboard aggregate, Attention Feed GET+close, Schedule GET, OmniChat, Waitlist CRUD, Forms CRUD | Метрики «лиды»/«отмены»; Feed claim; suggest-slots; создание брони из waitlist; form send-link |
| Фаза 3 | GET по id для patient, booking, doctor, service | Единый «богатый» контракт по вкладкам (вложенные коллекции или явные подзапросы) |
| Фаза 4 | CRM pipelines/stages/leads, PATCH stage; Tasks CRUD; Finance cashboxes + list transactions; Booking complete + ERP | Агрегаты сумм по этапам CRM; Tasks source=ai + claim; POST finance/transactions; AI Marketing Advisor |
| Фаза 5 | Recall, частично attribution | admin/search; POST ai/agent; виджет спасённой выручки; Retention AI (сегменты, офферы, ROI); Media, Export Builder, Full Backup |
| Loyalty Engine | SubscriptionPackage, CustomerSubscription, SubscriptionUsage, use_subscription_for_booking, patient_loyalty API | FamilyLink; контракт Checkout Hub (eligible subscriptions); Liability Dashboard; Celery check_expiring_packages; уточнение COUNT/BALANCE |

---

## Часть 4. Рекомендуемый порядок для @ARCH (выполнено)

1. **Структурировать** этот список в отдельном артефакте (например по приоритету P0–P2, по зависимостям от фронта). → **Сделано:** `docs/ARCH_BACKEND_GAPS_STRUCTURED.md`
2. **Зафиксировать контракты** (пути, методы, тела запросов/ответов) для каждого пункта в TPF_* или TECH_PASSPORT_BACKEND. → **Контракты зафиксированы** в промпте для @DEV.
3. **Написать промпт для @DEV** по реализации недостающего бэкенда (пошагово, с тестами и критериями приёмки), без дублирования уже существующего кода. → **Сделано:** `docs/dev_artifacts/DEV_ARTIFACT_BACKEND_IMPLEMENTATION.md`

---

*Документ подготовлен по результатам сверки `docs/DEV_MASTER_PROMPT.md` (1–408) и кодовой базы `src/`. Все «зерна» из DEV_MASTER_PROMPT и сценарий Loyalty & Wealth Engine (Gemini) учтены.*
