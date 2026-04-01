# REV_RAG_MAP_INNOVATIONS — Карта новшеств и возможностей UI/UX Business OS

> **Префикс REV_** — документы «революции» операционной системы (анализ, критерии, карты).  
> **Назначение:** Единая RAG-карта всех инноваций из TECH_PASSPORT_FRONTEND_UI_LOGIC: каждая фича привязана к страницам, эндпойнтам и сущностям. Используется для поиска и внедрения.

**Источник:** `TECH_PASSPORT_FRONTEND_UI_LOGIC.md` (полный документ).  
**Связь:** `REV_CRITERIA_IMPLEMENTATION.md`, `TPF_MASTER.md`, `TPF_MODULE_*.md`.

---

## 1. Универсальные паттерны (применяются везде)

| Паттерн | Описание | Где применять | Backend/API связь |
|--------|----------|----------------|-------------------|
| **Drawer > Modal** | Создание/редактирование только в `<Drawer position="right" size="lg">`. Modal — только Confirm/Alert. | Все сущности: Task, Booking, Patient, Service, Doctor, Lead, Cashbox, Form. | Любой CRUD-эндпойнт сущности. |
| **ActionMenu в строке** | В каждой строке таблицы справа `ActionIcon` (три точки) → `<Menu>` с действиями. | Все таблицы: пациенты, записи, врачи, услуги, лиды, кассы, задачи, шаблоны форм. | Эндпойнты действий (copy, cancel, send link, delete). |
| **EmptyState** | При `length === 0` — `<EmptyState>` с иконкой, текстом и Primary CTA. | Все списки и таблицы. | Те же GET-эндпойнты списков. |
| **Data Density** | Таблицы компактные (`verticalSpacing="sm"`), без визуального шума. | Все таблицы. | — |
| **Zero-Click Context** | `HoverCard`/`Tooltip` на имя пациента/врача: телефон, LTV, след. визит. | Везде, где отображаются имена (чат, календарь, CRM, задачи). | GET patient/doctor summary или вложенные поля в ответах. |
| **Keyboard First** | `useHotkeys`: Cmd+K Spotlight, Cmd+Enter отправка, Escape закрытие. | Глобально + OmniChat, формы. | Spotlight может вызывать search/ai endpoints. |
| **Optimistic UI** | Мутации через React Query: `onMutate` обновляет UI до ответа сервера. | Календарь (drag), CRM (drag), задачи (статус), чат (отправка). | PUT/POST с идемпотентностью где нужно. |
| **Skeleton Loaders** | Вместо `<Loader>` — `<Skeleton>` по контуру контента. | Все страницы с загрузкой данных. | Те же GET. |
| **Relational Integrity** | Формы без «висящих» сущностей: Task → assignee_id, due_date; Transaction → cashbox_id, amount, type, category. | Формы создания задач, финансов. | Валидация на бэкенде (required fields). |

---

## 2. Каркас приложения (App Shell)

| Элемент | Описание | Страницы/компоненты | API/Backend |
|---------|----------|----------------------|-------------|
| **Без Header** | Верхний глобальный Header удалён. | `AdminLayout.tsx` | — |
| **Dark Sidebar** | Navbar тёмный (`dark.8`), Main светлый (`gray.0`). | Layout | — |
| **Collapse Sidebar** | Кнопка свёртки: 260px ↔ 80px (иконки). | Layout | — |
| **Группы меню** | OPERATIONS, CRM, ERP, SETTINGS с заголовками. | Layout | — |
| **Context Bar** | В каждой странице сверху: заголовок + главные кнопки. | Все admin-страницы | — |
| **Spotlight Cmd+K** | Глобальный поиск: пациенты, записи, переходы. | Глобально | GET search или `/api/v1/admin/search` (если ввести). |
| **AI Command Line** | В Spotlight — вкладка «Спросить AI»: текст → вызов AI-агента. | Spotlight | POST ai/agent или function-calling endpoint. |

---

## 3. Модуль: Dashboard (Action Center)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| 4 метрики + динамика | Записи сегодня, Выручка, Новые лиды, NPS/Отмены; зелёная стрелка % к вчера. | `/admin`, Dashboard | Агрегаты: bookings, revenue, leads, cancellations (существующие или новые). |
| Attention Feed | Лента: просроченные задачи, непрочитанные чаты, отмены, требующие звонка. | Левая колонка Dashboard | `GET /api/v1/admin/attention-feed` или аналог. |
| Таймлайн расписания | Карточки ближайших записей на сегодня. | Правая колонка Dashboard | `GET /api/v1/admin/clinics/{id}/schedule` + фильтр today. |
| Sparkline + % роста | Микро-график под виджетами, % к прошлой неделе. | Top Bar | Те же агрегаты с разбивкой по дням. |
| Алерты с кнопками | «Иванов отменил 15:00» → кнопка «Предложить листу ожидания». | Attention Feed | Actions: suggest waitlist, open checkout. |
| Owner Morning Brief | Утренняя сводка в Telegram (вне UI). | — | Celery + Telegram; конфиг в настройках. |

---

## 4. Модуль: OmniChat (Smart Hub)

| Инновация | Детали | Компонент | Эндпойнты |
|-----------|--------|-----------|-----------|
| Smart Inbox | Бейджи: [Ждёт ответа], [AI ведет], [Черновик]. Фильтры-таблетки. | Левая колонка | Chats list + computed flags (last_message from client, ai_enabled). |
| Preview системных ивентов | «🔄 AI записал на 14:00», «💳 Оплата 5000₽ получена». | Список чатов | Messages с type=system или enrichment в списке чатов. |
| AI Magic Suggestions | 3 кнопки над полем ввода по контексту последнего сообщения. | Центр | POST ai/suggest-replies или в составе chat context. |
| Rich Message Bubbles | Ссылка на оплату → Card: «Счет #123 5000₽ [ОПЛАЧЕНО/ОЖИДАЕТ]». | Лента сообщений | Payment status в реальном времени (webhook или poll). |
| Action Bar | Иконки: Запись, Счёт, Анкета, AI вкл/выкл. | Под полем ввода | Bookings create, Payments create, Forms send, AI toggle. |
| CRM Context | Пациент, этап воронки (dropdown), след. визит, заметки (жёлтый стикер). | Правая колонка | Patient, LeadCard/LeadStage, Bookings next, internal_notes. |
| Кнопка «Создать запись» | Drawer с предзаполненным телефоном. | Правая колонка | POST admin/bookings с patient_id/phone. |
| Hotkeys | Cmd+J фокус поиск чатов, Cmd+Enter отправить, Escape закрыть. | Чат | — |

---

## 5. Модуль: CRM & Sales (Kanban)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Столбцы = LeadStage | Горизонтальный скролл, колонки по этапам. | CRM Kanban | GET lead_stages, GET lead_cards по stage. |
| Карточка лида | Имя, Бюджет, иконка источника (TG/WA/Site), дата контакта, тег «AI Активен». | Карточка | LeadCard + channel + last_message_at, ai_active. |
| Drag-and-Drop | Перетаскивание карточек между колонками. | Kanban | PUT lead_cards/{id} (stage_id), optimistic. |
| Drawer по клику | История чата + «Сгенерировать ссылку на предоплату». | Правая панель | Omnichannel messages, POST payments (link). |
| Суммы на столбцах | «Думают (5) — 150 000 ₽». | Шапка колонки | Агрегат sum(budget) по stage. |
| Lead Rotting | Карточка «краснеет», если в «Думает» > 2 дней. | Карточка | Вычисление по updated_at/stage. |
| Иконка канала → Drawer чата | Клик по WA открывает чат в Drawer справа. | Карточка | Тот же OmniChat, контекст по contact_id. |

---

## 6. Модуль: Задачи (Task Manager)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Таблица + Канбан | Два режима отображения. | Tasks | GET tasks (list). |
| Карточка | Title, Badge приоритет, аватар исполнителя, дата (красная если просрочено). | Оба режима | Task + assignee, due_date. |
| «Задачи от AI» | Отдельный пул, кнопка «Принять в работу». | Tasks | GET tasks?source=ai, PATCH task (assign to me). |
| Форма задачи | assignee_id, due_date, linked_entity (Patient/Lead/Booking). | Drawer | POST/PUT tasks. |
| AI-задачи с иконкой | IconRobot, градиентная рамка. | Карточка | task.source === 'ai'. |
| Linked Entity | Кнопка «Открыть чат с клиентом» внутри задачи. | Drawer/карточка | Ссылка на chat/patient/booking. |
| Micro-Actions | В карточке: кнопка звонка, «Отправить ссылку в WhatsApp». | My Focus | useRouter + chat/payment. |
| Time-Bomb | Красная пульсирующая рамка при задаче > 2 ч без реакции. | My Focus | due_at / created_at. |

---

## 7. Модуль: Финансы и Склад (ERP)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Кассы | Название, баланс. Кнопки: Внести, Изъять, Перевод. | Finance / Cashboxes | GET/POST cashbox, POST transaction (type in/out/transfer). |
| Форма транзакции | cashbox_id, amount, type, category — обязательно. | Drawer | POST transactions (validation). |
| Техкарты в услуге | Вкладка «Расходники» в Drawer услуги: Product + Amount. | Service Drawer | ServiceConsumable или аналог. |
| Checkout Hub | При «Завершить визит»: чек, оплата (касса), склад (accordion). | Booking Drawer / отдельный экран | Bookings complete, Payments, consumables write-off. |

---

## 7b. Модуль: Loyalty & Packages (Loyalty Engine)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Digital Pass (PWA) | Карточки абонементов в стиле Apple Wallet: прогресс-бар, дата сгорания, кнопка «Записаться по абонементу» → мастер с фильтром услуг пакета; чекаут «Оплачено абонементом». | PWA / Профиль | GET patient/loyalty/subscriptions (name, remaining/total, expires_at, services_included). |
| Family Sharing | В Drawer пациента вкладка «Абонементы», кнопка «+ Добавить члена семьи» → Spotlight по пациентам; привязанный видит карту с пометкой «Доступ: Иван И.» | Patient Drawer, /admin/loyalty | FamilyLink CRUD; при списании проверка owner/shared_with. |
| Auto-Checkout | В Checkout Hub при подходящем пакете — галочка «Списать 1 визит с абонемента»; подтверждение без дублирования оплаты. | Checkout Hub | GET checkout-info (eligible subscriptions), POST complete с use_subscription_id. |
| Liability Dashboard | «Деньги в воздухе» (Unearned Revenue) — сумма неотработанных абонементов. | Finance / вкладка или блок | GET admin/clinics/{id}/finance/liability. |

---

## 8. Модуль: Формы (Paperless)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Список шаблонов | Кнопка «Создать шаблон». | Forms / Settings | GET/POST form_templates. |
| «Отправить форму» | В контекстном меню пациента/записи → уникальный URL в WA/SMS. | ActionMenu Patient/Booking | POST form/send-link (patient_id, template_id). |

---

## 9. Матрица обогащённых сущностей (Entity Tabs)

| Сущность | Вкладки (кратко) | Открытие | Ключевые API |
|----------|------------------|----------|--------------|
| **Patient** | Header (LTV, теги); Инфо; Визиты; Финансы; **Абонементы** (пакеты, Family Sharing); Медкарта/Заметки; Коммуникации/Чат. | Drawer или `/admin/patients/[id]` | Patient CRUD, bookings, payments, loyalty/subscriptions, family_links, notes, comms. |
| **Booking** | Детали; Услуги и чек; Расходники; Задачи. | Клик по слоту / из списка | Booking CRUD, services, consumables, tasks. |
| **Employee/Doctor** | Профиль; Расписание; Зарплата; Услуги (чекбоксы). | Drawer | Doctor CRUD, working_hours, payroll policy, service_doctor. |
| **Service** | Описание; Исполнители; Техкарта; Онлайн-запись (флаги). | Drawer | Service CRUD, consumables, service_doctor. |

---

## 10. Расписание (Smart Calendar)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Drag & Drop | Перетаскивание карточек между врачами/временем. | Schedule | PUT booking (doctor_id, slot), optimistic. |
| Ghost Slots (AI) | Бледно-зелёные «идеальные окна» при создании записи. | Модал/Drawer создания | GET schedule + алгоритм «дыр» (бэкенд или фронт). |
| Sidebar Waitlist | Панель листа ожидания; перетащить пациента в слот. | Schedule | Waitlist list, POST booking из waitlist. |

---

## 11. Маркетинг и аналитика

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Top Bar метрики | Бюджет, Выручка с рекламы, CAC, ROMI. | Analytics/Marketing | Агрегаты по UTM. |
| Funnel Chart | Трафик → Лиды → Записались → Оплатили + конверсии. | То же | Attribution pipeline. |
| Таблица кампаний | По UTM_Source; Drill-down в Drawer с пациентами. | То же | GET campaigns/patients by source. |
| AI Marketing Advisor | Текстовые инсайты («акция X принесла…», «VK конвертирует хуже»). | Блок на странице | POST ai/marketing-insights или отчёт. |

---

## 12. Лента внимания и Mission Control

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Attention Feed (карточки) | Типы: Критично, Финансы, AI-Ассистент, Склад; кнопки действий. | Dashboard / отдельная | GET attention-feed, PATCH claim. |
| My Focus | Личные задачи по SLA, сортировка по времени реакции. | Правая колонка | GET tasks (assignee=me, sort by sla). |
| «Взять в работу» | С алерта в Feed → перенос в My Focus. | Feed | PATCH task assign. |
| AI Supervisor Summary | Вечерний отчёт владельцу (вне UI или виджет). | Owner | Celery + report generation. |

---

## 13. Retention (Smart Retention Engine)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| AI Segments | Когорты: «На грани ухода», «Охотники за скидками», «VIP в спячке», «Пора на процедуру». | Retention | GET segments (predefined + AI). |
| AI Hyper-Personalization | Генерация персональных офферов по сегменту. | Конструктор кампании | POST ai/generate-offers. |
| Waterfall | WhatsApp → Push (24ч) → SMS (VIP). | Кампания | RecallCampaign + каналы. |
| ROI кампании | Воронка: Отправлено → Прочитано → Перешли → Записались → Оплатили (сумма). | Карточка кампании | GET campaign stats. |

---

## 14. Omni-Vault (Медиа и экспорт)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Media Gallery | Masonry, фильтры (рентген, видео, за сегодня). | Медиа-хаб | GET media_assets (poly: patient/booking/message). |
| Overlay при наведении | На карточку файла: аватар клиента, иконка канала (TG/WA), дата. Контекст без клика. | Карточка в галерее | Те же media_assets + связь с контактом/каналом. |
| Контекст по клику | Drawer: файл + чат/визит. | Drawer | Media + conversation/booking. |
| Голосовые + транскрипт | Waveform (библиотека типа wavesurfer.js или аналог) + текст авто-расшифровки (Whisper). | Чат + галерея | Media transcript, storage S3. |
| Data Export Builder | Drag колонок, превью таблицы, Excel/CSV. | Настройки/Экспорт | POST export (columns, format). |
| Full Backup | Кнопка «Запросить бэкап» → прогресс → ссылка в Telegram. | Настройки | Celery backup task. |

---

## 15. PWA (Patient App)

| Инновация | Детали | Страница | Эндпойнты |
|-----------|--------|----------|-----------|
| Bottom Navigation | Главная, Запись, Чат, Профиль. | App layout | — |
| Next Visit Ticket | Билет с QR, адрес, «Добавить в календарь». | Home | GET patient/bookings (next). |
| Stories Bar | Горизонтальный скролл сторис (акции). | Home | GET stories/promo. |
| Booking Wizard | Визуальный выбор врача, карусель дат, слоты chips. | Запись | Doctors, schedule, POST booking. |
| Digital Wallet | Баланс кэшбэка, прогресс до VIP. | Профиль | Loyalty/balance. |
| Pull-to-Refresh | На записях и чате. | Список/чат | — |

---

## 16. Продвинутые фичи (из техпаспорта)

| Фича | Описание | Где | API |
|------|----------|-----|-----|
| **AI Revenue Hunter** | Ночной процесс: дыры в расписании → кандидаты (RAG) → авто-сообщения WA → бронь. | Бэкенд + виджет «Спасённая выручка» на Dashboard | Celery, AI, Booking, Omnichannel. |
| **Owner Morning Brief** | Сводка в Telegram утром. | Вне UI | Celery + Telegram. |
| **Premium Empty States** | Иллюстрация + CTA, не пустая таблица. | Везде пустые списки | — |

---

## 17. Индекс: страница → инновации

| Страница (admin) | Ключевые инновации из карты |
|------------------|-----------------------------|
| `/admin` (Dashboard) | Метрики+динамика, Attention Feed, Таймлайн, Sparkline, алерты с кнопками. |
| `/admin/schedule` | Drag&Drop, Ghost Slots, Waitlist sidebar. |
| `/admin/chat` | Smart Inbox, AI Suggestions, Rich Bubbles, Action Bar, CRM Context, Hotkeys. |
| `/admin/crm` | Kanban, суммы на столбцах, Lead Rotting, Drawer чата. |
| `/admin/tasks` | Таблица+Канбан, AI-задачи, Micro-Actions, Time-Bomb, My Focus. |
| `/admin/finance` | Кассы, транзакции, Checkout Hub, Liability (Unearned Revenue). |
| `/admin/loyalty` | Пакеты (шаблоны), проданные абонементы, Family Sharing из карточки пациента. |
| `/admin/forms` | Шаблоны, «Отправить форму» из контекста. |
| `/admin/patients`, карточка | Patient 360° (вкладки), EmptyState. |
| `/admin/bookings`, слот | Booking Drawer (вкладки), Checkout. |
| `/admin/analytics` | Funnel, таблица кампаний, Drill-down, AI Advisor. |
| `/admin/retention` | AI Segments, Hyper-Personalization, Waterfall, ROI. |
| Медиа/Экспорт | Masonry, транскрипты, Export Builder, Backup. |
| Layout | Dark Sidebar, Collapse, Context Bar, Cmd+K, AI Command. |

---

## 18. Индекс: эндпойнт → затронутые инновации

Используется для планирования бэкенда и контрактов.

- **Attention / Feed:** `GET attention-feed`, `PATCH claim`, задачи по SLA.
- **Search / Spotlight:** `GET admin/search` (пациенты, записи), `POST ai/command` (AI Command Line).
- **Chat:** список с флагами (ждёт ответа, AI), suggest-replies, payment status для Rich Bubbles.
- **CRM:** lead_cards по stage, агрегаты sum по stage, PATCH stage (drag).
- **Tasks:** source=ai, assignee, due_date, linked_entity; claim from feed.
- **Finance:** cashbox, transactions (in/out/transfer), категории; liability (Unearned Revenue).
- **Loyalty:** `GET patient/loyalty/subscriptions` (Digital Pass); checkout-info (eligible subscriptions), complete с `use_subscription_id` (Auto-Checkout); admin/loyalty/packages/{id}/family (FamilyLink); GET admin/clinics/{id}/finance/liability (Liability Dashboard).
- **Export/Backup:** export builder (columns), full backup task.
- **Media:** media_assets polymorphic, transcript, S3.
- **Recall:** segments (AI), generate-offers, campaign stats с воронкой.

---

*Конец RAG-карты. При внедрении: сначала `REV_CRITERIA_IMPLEMENTATION.md`, затем `TPF_MASTER.md` и модульные `TPF_MODULE_*.md`.*
