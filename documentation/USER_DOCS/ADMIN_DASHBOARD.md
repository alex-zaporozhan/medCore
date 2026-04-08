# Лента / дашборд админки

> **Аудитория:** сотрудник клиники.  
> **Источник UI:** `frontend/src/admin/pages/AdminDashboardPage.tsx` (не путать с отдельными отчётными страницами `/admin/reports`).

## Адрес

`/admin` — индексный маршрут внутри `AdminAuthGuard` → `AdminClinicProvider` → `AdminLayout`.

## Состав экрана (по коду)

Экран **не сводится только к staff feed**: это **дашборд дня + коллаборация**.

### 1. Верхняя зона

- **ContextBar:** заголовок **«Лента»**.
- Кнопка **«Приоритетные сообщения»** → `/admin/attention` (`ROUTE_PATHS.admin.attention`). Стиль **filled/orange** и счётчик, если есть непрочитанные объявления с `requires_ack` и без `acknowledged_by_me` в данных ленты (`staffPosts`).

### 2. Фильтр клиник

- При наличии нескольких клиник — **MultiSelect «Клиники»** (пусто = все выбранные для метрик дня).

### 3. Метрики дня (отчётный API)

Данные: **`useAdminReportsDashboardByClinics`** (день, granularity `"day"`, выбранные клиники).

Карточки (примеры подписей в UI):

- **Всего посещений** — `bookings_completed` (завершённые записи).
- **Новые пациенты** — `new_patients` за день.
- Далее в сетке используются поля ответа дашборда (пульс загрузки, чаты и т.д. — см. разметку ниже по файлу).

**Кто видит выручку на дашборде:** `canViewRevenueDashboard` — роль **owner** **или** одновременно права **`view_marketing_analytics`** и **`view_finance`** (не «любой admin»).

### 4. Staff feed (лента персонала)

- Загрузка постов: **`useStaffFeedPosts(20)`**.
- Публикация постов и вложений: права **`manage_staff_collab`** (`canPostToStaffFeed`); иначе композер недоступен.
- API вложений превью: `GET /v1/admin/staff/feed/attachments/{id}/file` (blob); загрузка после создания поста: `POST /v1/admin/staff/feed/posts/{id}/attachments`.
- Поддерживаются вложения изображение / аудио / видео / скачиваемые файлы (см. `StaffFeedAttachmentPreview`).

### 5. Прочее на странице

- Блоки **Revenue Hunter** при включённом флаге (`isRevenueHunterEnabled`, сохранённые настройки клиники) — см. хуки в том же файле.
- При загрузке/ошибке отчёта показываются скелетоны или **`QueryErrorAlert`**, плюс текст **`BACKEND_HINT`** (проверка бэкенда на порту 8000, ссылка на `documentation/DEVELOPMENT.md`).

## Навигация в сайдбаре

Пункт **«Лента»** в группе «СОТРУДНИКИ» (`AdminLayout.tsx`) ведёт на `/admin`.

## См. также

- [ADMIN_STAFF_CHAT.md](./ADMIN_STAFF_CHAT.md) — отдельный чат команды  
- [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.2  
- [../API_V1_ROUTER_MANIFEST.md](../API_V1_ROUTER_MANIFEST.md) — где живут отчётные и staff API
