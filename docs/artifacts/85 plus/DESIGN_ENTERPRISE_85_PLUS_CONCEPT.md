# DESIGN_ENTERPRISE_85_PLUS_CONCEPT

## 1. Executive summary

- Текущая оценка UI зрелости: **7.6 / 10** (сильная база темы и shell, но есть модульная неоднородность).
- Основной риск: разная плотность интерфейсов и локальные стиль-паттерны в admin-экранах создают когнитивный шум.
- Цель 85+: перевести UI в режим **single design language** с измеримыми критериями (tokens, component contracts, state model, accessibility baseline).
- **Каноническая визуальная линия Enterprise 85+:** палитра **Swiss Slate / Ink** (глубокий сине-графит `#1c2e45` как brand primary, холодные нейтрали, премиальные тени и дисциплинированный motion). Полная спецификация раскрытия цвета, **зеркальности/симметрии**, эффектов и анимаций — **§3.6** (в т.ч. §3.6.2a, §3.6.11–3.6.13). **Пиксельный паритет** со свотчем «§1 — Swiss Slate / Ink» в `DESIGN_PALETTE_SPECTRUM_SWATCHES.html` зафиксирован в коде: `frontend/src/theme.ts`, `frontend/src/index.css`, `docs/artifacts/85 plus/DESIGN_TOKENS_85_PLUS.json` (см. §3.6.2a). Опции альтернативных направлений (секции 2–5 HTML) — только для сравнения, **не** смешивать с каноном в одном продукте.

Top-10 критичных проблем:
1. Нет единого контракта плотности данных для dashboard/reports/tasks таблиц.
2. Разная подача заголовков и context-actions между страницами.
3. Не везде единая модель `empty/loading/error`.
4. Дубли drawer/modal-стилей на уровне локальных компонентов.
5. Недостаточно формализованы semantic colors (warning/info/ai) для сложных сценариев.
6. Разные практики фильтров и toolbar-элементов.
7. Недостаточная стандартизация карточек сущностей (patient/booking/doctor/service).
8. Не везде одинаково выдержан sticky context bar.
9. Нет формального accessibility checklist для каждого релиза.
10. Нет единого входного шаблона для Box/Enterprise UX-различий.

---

## 2. Screen inventory by module

### Admin core
- `AdminDashboardPage`
- `AdminBookingsPage`
- `SchedulePage`
- `AdminStaffCalendarPage`
- `AdminTasksPage`
- `AdminReportsPage`
- `AdminFinancePage`

### CRM / marketing / retention
- `AdminSalesPipelinePage`
- `AdminPatientsPage`
- `AdminRecallPage`
- `AdminWaitlistPage`
- `AdminRetentionPage`
- `AdminMarketingPage`
- `AdminDiscountsPage`
- `AdminPrepaymentPage`

### Omni / communication
- `AdminOmniChatPage`
- `AdminChatPage`
- `AdminStaffChatPage`
- `AdminOmniChannelsPage`
- `AdminChannelsPage`
- `AdminEmergencyNotificationsPage`
- `AdminNotificationPolicyPage`
- `AdminOmniVaultPage`

### Settings / integrations / governance
- `AdminSettingsPage`
- `AdminIntegrationsPage`
- `AdminPaymentGatewayPage`
- `AdminAiSettingsPage`
- `AdminOmniAiSettingsPage`
- `AdminAiReportsPage`
- `AdminClinicsPage`
- `AdminAdministratorsPage`
- `AdminClientReferencePage`
- `AdminAgreementsPage`
- `AdminFormsPage`
- `AdminKnowledgePage`
- `AdminStylingPage`
- `AdminServicesPage`
- `AdminDoctorsPage`

### Patient app
- `HomePage`
- `BookingWizardPage`
- `BookingSuccessPage`
- `ChatPage`
- `FeedPage`
- `FormsPage`
- `HistoryPage`
- `LoyaltyPage`
- `ProfilePage`
- `LoginPage`
- `OAuthResultPage`

---

## 3. Unified design system spec (target)

### 3.1 Typography
- Family: `Inter, system-ui, -apple-system, sans-serif`
- Base scale: `12 / 14 / 16 / 18 / 20 / 24 / 28`
- Heading policy:
  - H1: page-level strategic screens only
  - H2/H3: module and subsection
  - Body: default `14` for dense views, `16` for form-heavy flows
- Numeric readability: tabular nums for finance/reports/tables.
- **Swiss Slate / Ink:** заголовки страниц — максимальная плотность чернил (`text main`), без цветного текста для H1/H2; акцент brand — только в действиях и навигации (§3.6.3).

### 3.2 Color roles (канон Swiss Slate / Ink)
- **Brand primary (ink):** шкала **ink-navy** — основные CTA, активное состояние навигации, ключевые ссылки первого порядка, **единое** кольцо фокуса (тот же hue, не «чужой» синий). Референс: `--brand-600` / `#1c2e45`, hover `--brand-700` / `#152338`. Подробно §3.6.2.
- **Neutral:** холодный **slate** для поверхностей, текста, разделителей (`#f4f6f8` app → `#0f1419` ink text). Карточки — белые `#ffffff` с микрограницей.
- **Semantic (роли неизменны по смыслу; hex — как в свотче §1 Swiss, см. §3.6.2):**
  - Success: текст `#065f46`, фон `#ecfdf5` (Mantine `green.*` в теме)
  - Warning: `#b45309`, фон `#fffbeb` (`yellow.*` в теме для amber-оси)
  - Error / danger: `#b42318`, текст акцента `#7f1d1d`, фон `#fef2f2` (`red.*`)
  - Info = **холодный blue**, только для информационного смысла; **не** подменяет brand-ink и не смешивается с ним в одной кнопке без роли
  - AI-assist = violet (отдельный кортеж, не конкурирует с ink по площади)
- **Rule:** семантика и brand только через **role tokens** (`--semantic-success`, `--brand-*`, …); запрет ad-hoc hex в страницах. Любой полупрозрачный слой (focus, highlight строки) — из **RGB brand-ink**, не из дефолтного blue Mantine.

### 3.3 Elevation and surfaces
- Elevation levels **0–4** заданы для Swiss Slate / Ink в §3.6.4 (тени с подтоном `rgba(15, 20, 25, …)`, не чистый чёрный).
- Surfaces:
  - Base app background
  - Standard card background
  - Soft highlighted panel
  - Overlay/glass layers (лёгкий холодный оттенок, не «молочное» стекло без границы)

### 3.4 Spacing/grid
- Core spacing scale: `4/8/12/16/24/32`.
- Desktop grid: 12-column logical layout.
- Dense data screens: fixed row density and predictable vertical rhythm.

### 3.5 Motion/interactions (база; детализация §3.6.12)
- Duration: **120 / 180 / 240 ms** (micro / UI / panel).
- Easing: по умолчанию `cubic-bezier(0.33, 1, 0.68, 1)` (smooth deceleration); **не** вводить уникальные кривые на отдельных страницах.
- Focus ring: unified, **ink-tinted** (§3.6.5), видимый на всех фокусируемых элементах.
- **Запрет:** резкие bounce, длинные >400 ms анимации на кнопках, параллакс «ради красоты» в админке.

---

### 3.6 Swiss Slate / Ink — премиум-концепт: как раскрыть палитру «дорого»

Этот раздел — канон **визуального премиума** для Enterprise 85+: не только hex, но **где** цвет появляется, **как** ведут себя тени и **зачем** движение.

#### 3.6.1 Философия: «швейцарский» клинический люкс

- **Нейтраль = 90% экрана.** Продукт читается графитом, белым и холодным серым. Это создаёт ощущение дорогой полиграфии и приват-банка, а не стартап-дашборда.
- **Ink = редкая награда.** Появляется в момент решения: кнопка, активный пункт меню, выбранный фильтр, прогресс шага, ссылка первого порядка. Если ink «размазан» по фонам блоков — палитра дешевеет.
- **Семантика = сигнал, не украшение.** Зелёный/янтарный/красный только там, где есть смысл состояния; большие площади семантики запрещены.

#### 3.6.2 Карта токенов (референс для theme / CSS)

| Роль | Токен | Hex / значение | Применение |
|------|--------|----------------|------------|
| Фон приложения | `--surface-app` | `#f4f6f8` | `AppShell.Main`, холст |
| Подложка hover строки | `--surface-hover` | `#eef1f4` | строки таблицы, списки |
| Карточка / поле | `--surface-raised` | `#ffffff` | Card, Paper, inputs |
| Бордер по умолчанию | `--border-default` | `#e2e6ea` | карточки, инпуты в покое |
| Бордер сильнее | `--border-strong` | `#d0d7de` | secondary кнопки, разделители toolbar |
| Текст основной | `--text-primary` | `#0f1419` | заголовки, body |
| Текст вторичный | `--text-secondary` | `#5c6d7a` | подписи, мета |
| Brand 600 | `--brand-600` | `#1c2e45` | primary CTA, active nav |
| Brand 700 | `--brand-700` | `#152338` | hover pressed |
| Brand 50 (тинт) | `--brand-50` | `#e8eef3` | лёгкая подсветка выбранного без заливки всего блока |
| Focus ring | `--focus-ring` | `rgba(28, 46, 69, 0.22)` | единое кольцо + optional 0–3px spread |
| Success / Warn / Danger | см. таблицу §3.6.2a | без изменения ролей | фон светлый, текст тёмный в том же family |

**Правило миграции кода:** в Mantine `primaryColor` → **`brand`** (кортеж ink); ключ **`indigo`** в теме = **алиас** той же шкалы для совместимости; `--primary-alpha-*` в CSS из **RGB ink** (28, 46, 69) (см. `docs/design/DESIGN_PALETTE_PREMIUM_MANTINE.md`).

#### 3.6.2a Семантика и паритет со свотчем «§1 — Swiss» (репозиторий)

Ниже — **канонические hex** из `DESIGN_PALETTE_SPECTRUM_SWATCHES.html` (секция 1). Их нельзя «подменять» общими emerald/red из стока Mantine без обновления темы.

| Роль | CSS / токен | Hex | Mantine (тема) |
|------|-------------|-----|----------------|
| Success (текст/иконка) | `--success` | `#065f46` | `green.8` |
| Success (фон лёгкий) | `--success-bg` | `#ecfdf5` | `green.0` |
| Warning | `--warning` | `#b45309` | `yellow.7` |
| Warning bg | `--warning-bg` | `#fffbeb` | `yellow.0` |
| Danger | `--danger` | `#b42318` | `red.7` |
| Danger text | `--danger-text` | `#7f1d1d` | `red.9` |
| Danger bg | `--danger-bg` | `#fef2f2` | `red.0` |

**Brand (ink), ключевые ступени свотча:** `ink-50` `#e8eef3`, `ink-100` `#c5d4e0`, `ink-300` `#8a9faf`, `ink-500` `#4a5f73`, primary `#1c2e45`, hover `#152338`, `ink-900` `#0a1018` — отражены в `colors.brand` в `theme.ts` (10 ступеней с мостами между якорями).

**Нейтраль:** поверхности и лестница §1 (`#f4f6f8` … `#0f1419`) — в `colors.gray`.

**Артефакт токенов:** `DESIGN_TOKENS_85_PLUS.json` (поле `color.semantic` + `palette` в `meta`) должен совпадать с `:root` и темой после каждого изменения палитры.

**Частая ошибка (запрещена):** расхождение промежуточных ступеней brand (например `#9eb0be` вместо `#8a9faf` для «ink-300») или семантики в `:root` на старые `#10b981` / `#ef4444` / `#f59e0b` при том же каноне Swiss — ломает «дорогой» единый hue.

#### 3.6.3 Где и как «раскрывать» цвет (иерархия слоёв)

| Слой | Описание | Цветовое поведение |
|------|-----------|-------------------|
| **0** | Холст приложения | Только `--surface-app`; без brand-заливок. |
| **1** | Карточки, панели фильтров | Белый + `--border-default`; тень `elevation-sm`. |
| **2** | Поднятые элементы (dropdown, popover) | Белый + `elevation-md`; бордер чуть сильнее при необходимости. |
| **3** | Sticky context bar, закреплённый toolbar | `glass-light` или белый 0.92 opacity; **нижняя** граница `--border-default`; ink только у primary-кнопки справа. |
| **4** | Модалка, drawer | Поверхность белая/стекло; **backdrop** `rgba(0,0,0,0.08)`; тень «ореол» с ink-подтоном (§3.6.4). |

**Навигация:** активный пункт — фон `--brand-50` или белый + **левый индикатор 2px** `--brand-600` (дороже, чем заливка всей строки ярким цветом). Иконка и текст активного пункта — `--brand-600`.

**Таблицы:** zebra опционально через `--surface-hover`; выбранная строка — левая полоска `--brand-600` 3px + лёгкий тинт `--brand-50`, не сплошная заливка.

**Расписание / канбан:** статус — **полоска слева** + фон тинта 6–8% saturation; текст статуса — тёмный оттенок семантики, не неон.

#### 3.6.4 Тени и elevation (Crisp × Ink)

Тени всегда **двухслойные**, с подтоном холодного тёмного (как в палитре), не «серый RGB(0,0,0) на максимум».

| Уровень | Имя | Box-shadow (референс) | Контекст |
|---------|-----|------------------------|----------|
| E0 | none | — | flush к холсту |
| E1 | `elevation-xs` | `0 1px 2px rgba(15,20,25,0.05)` | разделители, микроподъём |
| E2 | `elevation-sm` | `0 1px 2px rgba(15,20,25,0.05), 0 4px 12px rgba(15,20,25,0.06)` | карточки, инпуты в покое |
| E3 | `elevation-md` | `0 4px 8px rgba(15,20,25,0.06), 0 16px 40px rgba(15,20,25,0.08)` | dropdown, модалка, важная карточка KPI |
| E4 | `elevation-focus` | внешнее кольцо + лёгкий подъём | карточка под курсором (hover), **не** постоянно на всех |

**Контекстные правила:**
- **Hover карточки сущности (patient, booking):** от E2 → E3 на **180ms**, без смещения layout (transform `translateY(-1px)` допустим максимум 1px).
- **Модалка:** E3 + лёгкий `backdrop-filter: blur(10px)` на оверлее (уже в теме); контент модалки не получает «радужную» тень.
- **Emergency / critical banner:** отдельный паттерн (оранжевый/красный) с **своей** тенью не смешивать с ink-тенью на той же оси — иначе грязь.

#### 3.6.5 Кнопки: варианты, состояния, уникальность

| Вариант | Визуал | Когда |
|---------|--------|--------|
| **Primary** | Заливка `--brand-600`, текст белый `#ffffff`, тень `elevation-xs` | Одна на блок: Создать, Сохранить, Отправить, Подтвердить |
| **Secondary** | Фон `#ffffff`, бордер `--border-strong`, текст `--brand-600` | Второе по важности действие рядом с primary |
| **Tertiary / ghost** | Без бордера, текст `--text-secondary`, hover `--surface-hover` | Отмена, Назад, «Пропустить» |
| **Danger** | Filled: красная шкала; или **light**: фон `#fef2f2`, текст `#7f1d1d`, бордер опционально | Удалить, отозвать |

**Микро-анимации (кнопка Primary):**
- **Hover:** фон `--brand-700`, тень E2→slightly stronger за **180ms**, `ease` как §3.5.
- **Active / pressed:** фон на 5–8% темнее hover или лёгкий inset-темнота (`box-shadow: inset 0 1px 2px rgba(0,0,0,0.12)`), длительность **120ms**.
- **Loading:** не менять ширину кнопки; спиннер **белый** на primary; текст «Сохранение…» с `opacity 0.85`. Запрет пульсации всей кнопки.
- **Disabled:** фон `#c5ccd4` или нейтраль 300, текст белый/серый с контрастом WCAG; **без** тени; курсор `not-allowed`.

**Уникальный «дорогой» штрих (ограниченно):** на **одной** главной CTA на экране (например «Записать пациента») допускается лёгкий **градиент** в пределах ink: `linear-gradient(180deg, #1f3550 0%, #1c2e45 100%)` — едва заметный; не на каждой кнопке.

#### 3.6.6 Стекло, модалки, drawer

- **Glass:** `background: rgba(255,255,255,0.92)`; `backdrop-filter: blur(12px)`; нижняя граница `--border-default`. Не использовать серый полупрозрачный без белого — выглядит дёшево.
- **Drawer:** тень сторона E3; заголовок drawer — `--text-primary`, действие закрытия — tertiary. Primary в футере один.
- **Разделитель в модалке:** 1px `--border-default`, без двойных линий.

#### 3.6.7 Семантика рядом с ink

- Успех на фоне brand: иконка success зелёная, текст остаётся **нейтральным** или белым на зелёном бейдже — не смешивать зелёный текст на ink-фоне без дизайн-ревью.
- **Info** (blue): ссылки «Подробнее», бейджи «Новое» — cold blue; не окрашивать ими заголовки страниц.

#### 3.6.8 Данные: таблицы, графики, финансы

- **Строки:** tabular nums; цвет отрицательных значений — semantic danger **только** число, не вся ячейка.
- **Графики:** палитра серий — оттенки slate + один акцент `--brand-600` для «нашей» серии; избегать радуги по умолчанию.
- **Heatmap / плотность:** использовать ступени нейтрали 100–400, не семантические цвета без смысла.

#### 3.6.9 Разрешённые «премиум-эффекты» (короткий whitelist)

| Эффект | Где | Ограничение |
|--------|-----|-------------|
| Skeleton shimmer | Загрузка таблиц/карточек | Градиент `linear-gradient` с **нейтральным** бликом, длительность 1.2–1.5s, `prefers-reduced-motion: reduce` → статический skeleton |
| Ink pulse | Только AI/внимание к ассистенту | 1px ring `--brand-600` opacity animate **2s ease-in-out infinite** — только на микро-бейдже, не на пол экрана |
| Row highlight | Поиск/фокус строки | `--brand-50` фон на 300ms fade |
| Toast success | Успешное сохранение | Зелёный accent слева 3px + нейтральный фон toast |

**Запрет:** конфетти, частицы, неоновые glow вокруг карточек, анимация логотипа в цикле внутри админки.

#### 3.6.10 Patient app и единство бренда

- Тот же **ink** для primary CTA и ссылок первого порядка; фон patient может быть чуть теплее **только** если отдельный токен `--surface-app-patient` согласован — иначе сохранять `#f4f6f8` / белый для консистентности.

#### 3.6.11 Зеркальность, симметрия и «премиум-глубина»

Здесь «зеркальность» — **не** буквальный глянец или отражение логотипа на каждой кнопке, а **дисциплина композиции** и **редкие** стеклянные/глубинные эффекты в духе дорогого инструментального UI.

**Симметрия и ось**

- **Вертикальная ось списка/таблицы:** заголовок колонки, разделитель и контент выровнены по одной сетке; иконки действий в строке — одна колонка фиксированной ширины (не «пляшущие» кнопки).
- **Мастер–деталь (split view):** при двухпанельном layout (список слева, карточка справа) допускается **зеркальная симметрия отступов**: одинаковые `padding` у обеих панелей, общая базовая линия заголовков; разделитель между панелями — 1px `--border-default`, без двойной линии.
- **Модалки и drawer:** зона действий **симметрична по весу** — primary справа (LTR), secondary/tertiary слева; визуальный баланс «отмена легче, подтверждение тяжелее» сохраняется при любой ширине окна.
- **Центрирование:** hero-экраны пациентского приложения могут использовать центральную ось; **админка** — преимущественно левое выравнивание текста в формах (читаемость данных).

**«Отражение» и глубина (сдержанно)**

- **Glass (`backdrop-filter`):** создаёт ощущение **слоя стекла** над холстом — «воздух» между toolbar и таблицей. Не умножать blur на вложенных элементах (один раз на sticky, не стеклянная карточка внутри стеклянной панели).
- **Нижний блик на карточке (опционально):** едва заметный `linear-gradient` снизу вверх `rgba(255,255,255,0.4) → transparent` на **одной** KPI-плитке или промо-блоке — не на каждой карточке в списке; только при отдельном продуктовом решении.
- **Запрет:** `transform: scale` на hover для всей таблицы, «металлические» градиенты на кнопках кроме оговорённого в §3.6.5 одного градиента primary.

**Зеркальность состояний (UX)**

- Hover на строке таблицы и hover на **соответствующей** карточке в мастер–деталь должны давать **согласованный** сигнал: тот же `--surface-hover` или та же левая полоска brand, чтобы пользователь чувствовал единый объект данных.

#### 3.6.12 Эффекты и анимации: полная матрица

Все значения согласуются с §3.5; при `prefers-reduced-motion: reduce` — **мгновенная** смена состояния без анимации движения (opacity допустима ≤50ms).

**Длительности и кривые**

| Категория | ms | Easing | Примеры |
|-----------|-----|--------|---------|
| Micro | 120 | `ease-out` | pressed кнопки, чекбокс, переключатель |
| UI | 180 | `cubic-bezier(0.33, 1, 0.68, 1)` | hover кнопки/карточки, border/shadow, раскрытие аккордеона |
| Panel | 240 | то же | вход drawer, сдвиг split, появление модалки (совместно с Mantine transition) |
| Ambient | 1500–2000 | `ease-in-out` | только skeleton shimmer (см. ниже); не циклы на CTA |

**Что анимируется (whitelist)**

| Элемент | Свойство | От → до | Примечание |
|---------|----------|---------|------------|
| Primary button | `background-color`, `box-shadow` | brand.6 → brand.7, E2 | без изменения размеров кнопки |
| Default button | `background-color` | white → gray.0 | §3.6.5 |
| Карточка сущности | `box-shadow`, опц. `translateY(-1px)` | E2 → E3 | 180ms, не на плотных списках >50 карточек без замера FPS |
| Строка таблицы | `background-color` | transparent → `--surface-hover` | без анимации height |
| Модалка / drawer | opacity overlay + transform контента | из темы Mantine | не увеличивать длительность >300ms |
| Фокус | `box-shadow` ring | 0 → 3px `--focus-ring` | мгновенно на Tab |
| Поиск по таблице | фон строки | `--brand-50` | fade 300ms §3.6.9 |
| Skeleton | `background-position` или opacity слоя | shimmer | нейтральный блик, не brand |

**Что не анимируется**

- Позиция скролла при смене фильтра (кроме программного scroll-into-view без «пружины»).
- Ширина колонок таблицы при первом рендере (resize — без анимации или ≤120ms linear).
- Любые **infinite** анимации кроме: skeleton (пока loading), ink-pulse на **одном** AI-бейдже §3.6.9.

**Связь с тенью и «дорогим» светом**

- Переход между E2 и E3 на hover **синхронизировать** с переходом цвета фона — один тайминг 180ms, чтобы не было эффекта «сначала тень, потом цвет».
- Для emergency-баннеров допускается лёгкий **pulsing opacity** текста или иконки (1–2 цикла), не бесконечно — иначе дешевизна и усталость.

#### 3.6.13 Связь §3.6.9 с полной матрицей

Короткий whitelist §3.6.9 остаётся **подмножеством** §3.6.12: любой новый эффект проходит проверку по таблице «Что анимируется» и по a11y §6. Не добавлять эффекты в прод без строки в этом документе и без owner в roadmap §8.

---

## 4. Canonical component patterns

- **Context bar**: sticky header with title + primary actions + optional breadcrumbs. Primary action — **ink** Primary button (§3.6.5); плотность как в §3.4; симметрия тулбара §3.6.11.
- **Data table**: unified toolbar/filter row + row states + empty/error fallback. Строки и тени — §3.6.3–3.6.4; hover строки — §3.6.12.
- **Entity drawers**: same header/action/footer contract for all entity types. Стекло и тени — §3.6.6; баланс футера — §3.6.11.
- **Modal**: unified glass style, consistent action layout. Один primary ink на футере; порядок кнопок и веса — §3.6.11.
- **Split / master–detail**: зеркальные отступы и согласованный hover список↔деталь — §3.6.11.
- **Forms**: field grouping, helper/error text hierarchy, section-level validation summary. Фокус инпутов — ink ring (§3.6.2).
- **Cards/KPI tiles**: one metric hierarchy model (value, delta, context). Число — `--text-primary`; дельта positive/negative — semantic green/red **точечно**.
- **Chat/Feed panels**: unified bubble, status and escalation visual semantics. Исключения emergency — отдельный семантический канал.

---

## 5. State and feedback model

For each screen mandatory states:
- `loading`: skeleton or progress placeholders (shimmer §3.6.9, тайминги §3.6.12, a11y §6).
- `empty`: explicit “что делать дальше” CTA (ink primary).
- `error`: user-readable + retry path.
- `partial failure`: degraded block isolated, page remains operable.
- `success`: lightweight confirmation (toast/inline) с семантикой §3.6.7.

Error messaging contract:
- technical detail hidden from end-user by default,
- action-oriented guidance always present.

---

## 6. Accessibility baseline (WCAG 2.1 AA)

- Contrast threshold met for text and critical controls (включая `--brand-600` на белом и белый на `--brand-600`).
- Keyboard-only path for all admin CRUD flows.
- Visible focus state: **ink ring** §3.6.2, не только browser default.
- Click target minimum 40x40 for primary actions.
- Semantic labels for icon-only actions.
- `prefers-reduced-motion`: правила §3.6.12 — отключать shimmer/pulse и трансформации, оставлять мгновенные state change.

Release rule: major admin screens cannot ship without accessibility spot-check evidence.

---

## 7. Box vs Enterprise UX policy

- Edition-based hiding must not create dead navigation.
- Disabled/forbidden enterprise features in Box:
  - either not rendered,
  - or rendered as explicit locked state with explanation.
- Screens must not imply data availability when server will deny access.

---

## 8. Prioritized redesign roadmap

### P0 (release-facing)
1. Unify `ContextBar` + page header/action composition across all admin pages (**ink** primary §3.6).
2. Standardize table/filter/empty/error states for Tasks/Reports/Patients/Bookings.
3. Normalize entity drawer patterns (booking/patient/doctor/service).

### P1 (productivity and consistency)
1. Canonical form layout with shared validation and helper-text model (focus ring §3.6.2).
2. Dashboard and reports density alignment; графики §3.6.8.
3. Chat/omni panels severity semantics and action prominence.

### P2 (scale and polish)
1. Motion token rollout по матрице §3.6.12 + короткий whitelist §3.6.9 / §3.6.13.
2. Visual debt cleanup for legacy local styles; точечный sweep ad-hoc hex вне §3.6.2a.
3. Theming cleanup for edition variants.

---

## 9. Definition of Done (Design handoff)

- Screen audit matrix completed for all in-scope pages.
- Token set **Swiss Slate / Ink** approved and mapped to frontend theme (`brand` / ink кортеж, alpha из одного hue).
- Component mapping (legacy -> canonical) accepted by DEV; кнопки и elevation соответствуют §3.6.
- P0/P1 implementation backlog created with acceptance criteria.
- All P0 findings have explicit owner and release target.
- **Премиум-палитра:** секция **§1 Swiss** в `DESIGN_PALETTE_SPECTRUM_SWATCHES.html` согласована с `theme.ts` / `index.css` / `DESIGN_TOKENS_85_PLUS.json` (§3.6.2a); семантика не откатывается к стоковым `#10b981` / `#ef4444` без согласования; зеркальность layout и motion — §3.6.11–3.6.12. См. также `DESIGN_PALETTE_PREMIUM_MANTINE.md`.
