# Дизайн-система ↔ код репозитория

**Назначение:** быстрая навигация от документов в `docs/design/` к файлам, где правится визуал. Канон палитры и теней — **Swiss Slate / Ink** (`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6). Нормы Mantine, глобальных CSS-переменных и **`AdminDrawer` vs сырой Mantine `Drawer`** — в [`../frontend/UI_THEME.md`](../frontend/UI_THEME.md) (этот файл — карта путей, не дублирует §компонентов темы).

**Обновлять** этот файл при появлении новых «точек входа» темы (новый shell, новый общий модал).

---

## Визуальные референсы (offline, без сборки)

| Файл | Назначение |
|------|------------|
| `docs/design/DESIGN_PALETTE_SPECTRUM_SWATCHES.html` | Полный спектр палитр (квадраты): Swiss Slate / Ink и альтернативы; секция календаря Swiss |
| `docs/design/DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html` | Варианты жёлтого/pending и карточки; **активный выбор в коде** — персиковый янтарь (`--calendar-scheduled-*`) |

После изменения hex в теме — сверить со свотчами и обновить `DESIGN_TOKENS_85_PLUS.json`.

---

## Ядро темы и глобальные токены

| Зона | Путь в репозитории | Заметка |
|------|-------------------|---------|
| Mantine `createTheme`, шкалы `brand` / `gray` / semantic, `primaryColor`, тени | `frontend/src/theme.ts` | `swissInk`, `slateCool`, `crispShadows` |
| CSS variables (`:root`): `--primary`, `--brand-*`, `--surface-*`, `--calendar-*`, focus ring | `frontend/src/index.css` | Паритет с JSON `DESIGN_TOKENS_85_PLUS.json` |
| Точка подключения темы | `frontend/src/main.tsx` — `import { appTheme } from "./theme"` → `<MantineProvider theme={appTheme}>` | PWA: дублирование провайдера в `AppLayout.tsx` с тем же `appTheme` |

---

## Shell админки и навигация

| Зона | Путь | Заметка |
|------|------|---------|
| Layout админки, AppShell | `frontend/src/admin/layouts/AdminLayout.tsx` | Активный пункт навигации — §3.6.3 концепта |
| Стили панелей / glass | `frontend/src/shared/ui/shellPanelStyles.ts` | `mergeModalStyles`, общие overlay |

---

## Переиспользуемые UI-примитивы (канон из `DESIGN_COMPONENT_MAPPING.md`)

| Документ / паттерн | Путь в коде |
|--------------------|-------------|
| Context bar (sticky заголовок страницы) | `frontend/src/shared/ui/ContextBar.tsx` |
| Админский drawer | `frontend/src/shared/ui/AdminDrawer.tsx` |
| Glass modal + merge стилей | `frontend/src/shared/ui/` — `GlassModal`, `shellPanelStyles.ts` → `mergeModalStyles` |
| Реэкспорт shared UI | `frontend/src/shared/ui/index.ts` |

**Тест на дисциплину drawer:** `frontend/src/__tests__/adminNoRawMantineDrawer.test.ts` — в админке не импортировать `Drawer` из `@mantine/core` напрямую.

---

## Расписание и календарь

| Зона | Путь | Документ |
|------|------|------------|
| Сетка слотов, статусы карточек | `frontend/src/admin/components/ScheduleCalendarGrid.tsx` | `DESIGN_CALENDAR_SEMANTIC_MAPPING.md`, `DESIGN_SCHEDULE_MODAL_SEMANTICS_85_PLUS.md`, `DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html` |
| Страница расписания врача | `frontend/src/admin/pages/SchedulePage.tsx` | |
| Календарь персонала | `frontend/src/admin/pages/AdminStaffCalendarPage.tsx` | |
| Хром полей сущности в drawer | `frontend/src/admin/components/entity/entityDrawerChrome.tsx` | §2 модалки в semantics |

---

## Entity drawers (booking / patient / doctor / service)

| Зона | Путь |
|------|------|
| Общий хром полей | `frontend/src/admin/components/entity/entityDrawerChrome.tsx` |
| Drawer записи и др. | `frontend/src/admin/components/entity/BookingEntityDrawer.tsx` и соседние `*EntityDrawer.tsx` |

---

## PWA / клиентское приложение

| Зона | Путь |
|------|------|
| Layout приложения | `frontend/src/app/layouts/AppLayout.tsx` |
| Тема для app | те же `theme.ts` / `index.css`, при расхождении — отдельный токен по концепту §3.6.10 |

---

## Как не рассинхронить док и код

1. Меняете hex / шкалу в `theme.ts` или `--*` в `index.css` → обновите **`DESIGN_TOKENS_85_PLUS.json`** и при необходимости §3.6.2a в концепте / свотчи HTML.  
2. Новый общий паттерн (новый тип модалки) → строка в этом файле + строка в `DESIGN_COMPONENT_MAPPING.md`.  
3. Новый экран админки → при необходимости строка в `DESIGN_SCREEN_AUDIT_MATRIX.csv`.

**Версия карты:** 2026-04-10 · @LEAD
