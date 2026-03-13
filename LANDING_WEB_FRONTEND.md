## Техпаспорт frontend (по коду): лендинг «Умная CRM»

**Источник данных:** только исполняемый код и конфиги фронтенда (`frontend/`).  
**Объект:** одностраничный промо‑лендинг продукта «Умная CRM» с лид‑формой, юридическими страницами и анонсом песочницы.

---

## 1. Стек и окружения

- **Язык:** TypeScript.
- **Фреймворк:** React 18.
- **Роутер:** `react-router-dom` v7 (`BrowserRouter`, `Routes`, `Route`).
- **UI‑библиотека:** Mantine v7:
  - `@mantine/core` — компоненты.
  - `@mantine/hooks` — хуки.
  - `@mantine/carousel` — карусель.
  - `@mantine/form` — формы и валидация.
- **Сборка и dev‑сервер:** Vite 6:
  - dev‑сервер: порт 3000.
  - proxy: `/api` → `http://localhost:8000`.
- **Иконки:** `@tabler/icons-react`.
- **Стили:** CSS (`src/index.css`) + тема Mantine (`src/theme.ts`).
- **Статические файлы:** `frontend/public/` (например, `robot.svg`, скриншоты экрана).

---

## 2. Точки входа и маршрутизация

### 2.1. HTML‑шаблон

- **Файл:** `frontend/index.html`.
- Содержимое:
  - `<div id="root"></div>` — корень SPA.
  - Подключение `src/main.tsx` как типа `module`.
  - Заполненные SEO‑мета‑теги:
    - `<title>`, `<meta name="description">`, `<meta name="keywords">`.
    - Open Graph (`og:*`) и Twitter (`twitter:*`).
    - `<link rel="canonical" href="https://goodcode-app.ru/">`.

### 2.2. Корневая инициализация

- **Файл:** `frontend/src/main.tsx`.
- Поведение:
  - Импорт CSS Mantine и `src/index.css`.
  - `ReactDOM.createRoot(document.getElementById('root')!)`.
  - Обёртка:
    - `<React.StrictMode>`.
    - `<MantineProvider theme={theme} defaultColorScheme="dark">`.
  - Рендерит `<App />`.

### 2.3. Корневой компонент и маршруты

- **Файл:** `frontend/src/App.tsx`.
- Использует `BrowserRouter`.
- Структура:
  - Обёртка `div.page-gradient`.
  - Фиксированный `Header` сверху.
  - `Routes`:
    - `/` → `LandingContent` (основной лендинг).
    - `/privacy` → `PrivacyPage` в `<main>` с отступами.
    - `/consent-promo` → `ConsentPromoPage` в `<main>`.
    - `/sandbox` → `SandboxPage` в `<main>`.
    - `/admin/leads` → `AdminLeadsPage` (внутренняя админ‑панель, маршрут не светится в публичном UI).
  - `Footer` внизу.
- Логика скролла:
  - В `useEffect` вешается обработчик `scroll`, который добавляет/убирает класс `is-scrolling` на `<body>` (оптимизация blur‑эффектов в CSS).

### 2.4. Состав `LandingContent` (маршрут `/`)

- Внутренний компонент `LandingContent` внутри `App.tsx`.
- Функции:
  - Определяет `isMobile` (медиазапрос `(max-width: 768px)`).
  - Следит за видимостью блока Hero через `IntersectionObserver`.
  - Управляет:
    - `showMobileCta` — показывать ли фиксированную CTA на мобайле.
    - `nearFooter` — подавлять ли CTA, если пользователь почти у футера.
- Рендерит (по порядку):
  - `Hero`.
  - `WhoFor`.
  - `UtpCards`.
  - `ProductBenefits`.
  - `CrmIncludes`.
  - `ScreensGallery`.
  - `Pricing`.
  - `GetStarted`.
  - `ContactsBlock`.
- Мобильная CTA:
  - Если Hero не в вьюпорте и `nearFooter === false`, рендерит фиксированный снизу стеклянный блок с кнопкой «Посмотреть демо» (якорь `#get-started`).

---

## 3. Конфигурация и вспомогательные модули

### 3.1. Конфиг фронтенда

- **Файл:** `frontend/src/config.ts`.
- Флаги:
  - `USE_HERO_CHAT_SCREENSHOT: true`:
    - Исторический флаг для переключения вида hero (скриншот чата vs шаблон).
    - В актуальном компоненте `Hero` фактически не используется → **рудимент / legacy‑флаг**.
  - `USE_LEGACY_HEADER_BRAND: false`:
    - При `true` бренд в шапке отображается как «AI чат‑центр».
    - При `false` — новый бренд «Умная CRM».
    - Используется в `Header` → активный флаг брендинга.

### 3.2. Хуки

- **`useReveal`** (`frontend/src/hooks/useReveal.ts`):
  - Возвращает `ref`.
  - В `useEffect` создаёт `IntersectionObserver` с `rootMargin: '80px 0px'`.
  - При пересечении:
    - Добавляет класс `reveal-visible` к элементу.
    - Удаляет наблюдение.
    - Управляет `will-change` для элемента и детей `.reveal-stagger > *`.
  - Используется секциями для плавного появления при прокрутке.

- **`useNoIndex`** (`frontend/src/hooks/useNoIndex.ts`):
  - При монтировании:
    - Находит/создаёт `<meta name="robots">`.
    - Сохраняет предыдущее значение и устанавливает `"noindex, nofollow"`.
  - При размонтировании:
    - Восстанавливает предыдущее значение или удаляет тег.
  - Используется на `/privacy` и `/consent-promo`.

### 3.3. API‑клиенты

- **Файл:** `frontend/src/api/leads.ts`.
- Интерфейс:
  - `LeadPayload` с полями `name`, `niche`, `url?`, `contact`.
- Функция:
  - `submitLead(data: LeadPayload): Promise<Response>`.
  - Формирует тело:
    - Поля формы.
    - `source: 'landing-audit-form'`.
    - `meta: { page: '/', anchor: '#get-started' }`.
  - Отправляет `fetch('/api/leads', {...})`.
  - Возвращает сырой `Response`.

- **Файл:** `frontend/src/api/adminLeads.ts`.
- Интерфейсы:
  - `LeadAdminSummary`, `LeadAdminDetail`, `LeadCommentDTO`, `LeadStatus` — DTO‑сущности, соответствующие админ‑API backend.
  - `LeadListResponse` — результат списка лидов (`items` + `total`).
- Функции:
  - `fetchLeads(params)` — забирает список лидов с фильтрами/пагинацией.
  - `fetchLeadDetail(id)` — получает детальную карточку лида с комментариями.
  - `createComment(id, text)` — добавляет комментарий к лиду.
  - `updateLeadStatus(id, status)` — меняет статус лида.
- Авторизация:
  - При каждом запросе добавляет заголовок `X-Admin-Token`, если в `localStorage` есть `adminToken`.

---

## 4. Основные визуальные блоки и потоки

### 4.1. Хедер и футер

- **`Header`** (`frontend/src/components/layout/Header.tsx`):
  - Использует `useWindowScroll` (Mantine).
  - Считает:
    - `scrollDirection` («up»/«down») для автоскрытия шапки.
    - Прогресс скролла (для прогресс‑бара сверху).
  - Состав:
    - Прогресс‑бар шириной по проценту прокрутки.
    - Фиксированный стеклянный `header` с blur, границей и тенью.
    - Бренд:
      - При `USE_LEGACY_HEADER_BRAND === true` — старый бренд.
      - Иначе — текущий бренд «Умная CRM» с иконкой.
    - Основная CTA‑кнопка «Посмотреть демо» (якорь `#get-started`).

- **`Footer`** (`frontend/src/components/layout/Footer.tsx`):
  - Стеклянный блок с:
    - Копирайтом.
    - Ссылкой на `/privacy`.
    - Упоминанием источника иллюстраций (Freepik).

### 4.2. Доменные секции лендинга (маршрут `/`)

Все лежат в `frontend/src/components/sections/` и реально используются через `LandingContent` (не являются рудиментами).

- **`Hero`**:
  - Главный оффер: «Запись, клиенты и чаты в одной программе. Без абонентской платы. Навсегда.»
  - Пункты преимуществ (нет скрытых подписок, меньше неявок, админ без стресса).
  - CTA: кнопка на `#get-started`.
  - Справа — стеклянная карточка с изображением `robot.svg` и анимацией.

- **`WhoFor`**:
  - Mantine‑карусель с карточками целевых ниш (салоны, клиники, студии, онлайн‑школы и т.д.).

- **`UtpCards`**, **`ProductBenefits`**, **`CrmIncludes`**, **`PainPoints`**, **`HowItWorks`**, **`Guarantee`**, **`AboutSystem`**, **`AboutMe`**:
  - Маркетинговые секции, раскрывающие ценность продукта:
    - UTP, решаемые боли, как система помогает, детали того, что входит в CRM, сценарии работы, гарантии и профиль автора.
  - Все подключены в основной компоновке или могут быть легко включены (в текущем коде — участвуют в реальном лендинге).

- **`ScreensGallery`**:
  - Грид скриншотов интерфейса (из `public/screens/*.jpg`).
  - Открывает полноэкранный просмотр в `Modal` с переключением изображений.

- **`Pricing`**:
  - Карточки тарифов («Старт», «Профи», «Бизнес») с набором фич.
  - CTA‑кнопки ведут в Telegram разработчика.

- **`GetStarted`**:
  - Левый блок: объяснение, что можно записаться на бесплатный аудит бизнеса.
  - Правый блок: стеклянная форма (см. далее).
  - Под формой: кнопка‑ссылка на `/sandbox` для будущей демо.

- **`ContactsBlock`**:
  - Крупные ссылки Telegram/e‑mail.

### 4.3. Юридические страницы

- **`PrivacyPage`** (`frontend/src/pages/PrivacyPage.tsx`):
  - Использует `useNoIndex`.
  - Содержит текст политики обработки ПД (структурированный текст в стеклянной карточке).

- **`ConsentPromoPage`** (`frontend/src/pages/ConsentPromoPage.tsx`):
  - Аналогично использует `useNoIndex`.
  - Содержит текст согласия на получение промо‑рассылок.

### 4.4. Песочница (демо)

- **`SandboxPage`** (`frontend/src/pages/SandboxPage.tsx`):
  - Статический текст: демо‑версия CRM «в разработке».
  - Кнопка ведёт на `"/#get-started"`.
  - Статус: **анонс будущей функциональности**, без фактического CRM‑интерфейса.

### 4.5. Внутренняя страница `/admin/leads`

- **Файл:** `frontend/src/pages/AdminLeadsPage.tsx`.
- Назначение: внутренняя админ‑панель для владельца, **не ссылкуется из публичного UI** (нужно знать URL).
- Основные элементы:
  - Блок авторизации:
    - Поле для `adminToken` и кнопка «Войти».
    - Токен сохраняется в `localStorage` и пробрасывается в заголовок `X-Admin-Token` при запросах.
    - При ошибке `401` токен очищается, показывается сообщение и панель просит ввести ключ заново.
  - Список лидов:
    - Таблица с колонками: дата, имя, ниша, контакт, статус, индикатор наличия комментариев.
    - Фильтры: статус (`all/new/in_progress/done`), даты `date_from`/`date_to`, строка поиска по имени/нише/контакту.
    - Пагинация: `page` / `page_size`, кнопки «Назад/Вперёд».
  - Панель деталей:
    - Отображает выбранный лид: базовые поля (`name`, `niche`, `contact`, `url`, `source`, `created_at`) и `meta.page`/`meta.anchor`.
    - Список комментариев с датой/автором и текстом.
    - Форма добавления комментария, вызывающая `POST /api/admin/leads/{id}/comments`.
    - Кнопки смены статуса (New / In progress / Done), вызывающие `PATCH /api/admin/leads/{id}/status`.

---

## 5. Поток лида (frontend‑часть)

### 5.1. Форма `GetStarted`

- **Файл:** `frontend/src/components/sections/GetStarted.tsx`.
- Состояние:
  - Mantine‑форма с полями:
    - `name`, `niche`, `url`, `contact`.
    - `terms_pd` (обязательно), `terms_promo` (опционально).
  - `status: 'idle' | 'submitting' | 'success' | 'error'`.
  - `errorMessage?: string`.
- Валидация:
  - `name` — обязателен, не пустой.
  - `niche` — обязателен, не пустой.
  - `contact` — обязателен, не пустой (формат не навязывается, текстовое поле).
  - `terms_pd` — должен быть `true`.
- Поведение onSubmit:
  - Приводит значения к аккуратному виду (например, пустой `url` → `undefined`).
  - Вызывает `submitLead`.
  - По результату:
    - `201` → `status = 'success'`, показывает благодарность.
    - Иные статусы → пытается прочитать `detail` из JSON‑ответа.
      - Если `detail` строка → выводит пользователю.
      - Иначе → дефолтное сообщение об ошибке.
    - Ошибки сети → отдельное сообщение «Ошибка сети…».

### 5.2. Интеграция с backend

- В dev‑режиме:
  - `fetch('/api/leads')` проксируется Vite на `http://localhost:8000/api/leads`.
- В проде:
  - Фронтенд собирается в Docker‑образ и обслуживает статические файлы.
  - Запросы `/api/leads` идут к backend‑контейнеру (внешний роутинг/реверс‑прокси не описан в этом репозитории, но соответствует docker‑compose).

---

## 6. CSS‑архитектура и тема

### 6.1. Тема Mantine

- **Файл:** `frontend/src/theme.ts`.
- Базовые настройки (по коду):
  - Базовый цвет и палитра `accent`.
  - Радиусы, шрифты, тени.
- Цель темы — синхронизировать дизайн Mantine‑компонентов с кастомными CSS‑токенами из `index.css`.

### 6.2. Глобальные стили

- **Файл:** `frontend/src/index.css`.
- Основные элементы:
  - CSS‑переменные (`:root`):
    - Цвета фона, поверхностей, текста, акцентов и свечения.
    - Радиусы, тени, размеры шрифтов.
    - Параметры анимаций reveal и float.
  - Классы:
    - `.page-gradient` — фоновый градиент + grid‑pattern.
    - `.section`, `.section-alt` — вертикальные отступы и layout для секций.
    - `.container-page` — максимальная ширина и отступы.
    - `.glass-card`, `.card-active`, `.content-card-hover` — стеклянные карточки и hover‑эффекты.
    - `.reveal`, `.reveal-visible`, `.reveal-stagger` — анимации появления.
    - Анимации `@keyframes` для декоративных элементов (float, glow и т.п.).
  - Оптимизация:
    - Селекторы вида `body.is-scrolling .glass-card { backdrop-filter: none; }` для снижения нагрузки при скролле.

---

## 7. Рудименты и исторические следы

- **Флаг `USE_HERO_CHAT_SCREENSHOT` в `config.ts`:**
  - В актуальном hero не используется.
  - Относится к старой версии блока (`chat screenshot`) → **рудимент**.

- **Legacy‑бренд в `Header`:**
  - Поддерживается через `USE_LEGACY_HEADER_BRAND`, но по умолчанию выключен.
  - Это не мёртвый код, а опция отката брендинга.

- **Sandbox‑страница:**
  - Является обещанием будущей демо‑версии, но не реальным интерфейсом CRM.
  - Технически маршрут активен, но бизнес‑функциональность **ещё не реализована**.

В остальном, все секции и страницы, лежащие в `src/pages` и `src/components/sections`, либо прямо подключены в `App.tsx`, либо участвуют в лендинге через `LandingContent`, и потому считаются **активной частью фронтенда**, а не рудиментами.

