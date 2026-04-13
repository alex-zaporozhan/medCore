# Дизайн-система проекта (канон)

**Назначение:** единая открытая папка для управления визуальным языком админки и PWA: токены, палитра **Swiss Slate / Ink**, компонентные контракты, бэклог и процесс внедрения.

**Роли:** @DESIGN (вердикт и спеки) · @LEAD (приоритет и ворота) · @FRONTEND / @DEV (реализация в `frontend/`) · @QA_ARCH (приёмка плотности и состояний).

**Источник правды в коде:** `frontend/src/theme.ts`, `frontend/src/index.css` — после изменения палитры обновляйте **`DESIGN_TOKENS_85_PLUS.json`** и **`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`** (§3.6). Детальная привязка к файлам фронта — **[DESIGN_CODE_MAP.md](./DESIGN_CODE_MAP.md)**. Инженерные слои SPA, Query и чеклист PR (не путать с визуальной концепцией): **[../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md)**.

---

## Карта файлов

| Файл | Содержание |
|------|------------|
| [DESIGN_CODE_MAP.md](./DESIGN_CODE_MAP.md) | **Навигация дизайн → код:** `theme.ts`, `index.css`, ContextBar, AdminDrawer, календарь, entity drawers |
| [DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md](./DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md) | Полная спека: типографика, цвет §3.6, elevation, кнопки, motion, a11y, Box/Enterprise, roadmap P0–P2, DoD |
| [DESIGN_TOKENS_85_PLUS.json](./DESIGN_TOKENS_85_PLUS.json) | Машиночитаемые токены (цвет, spacing, shadow, calendar); `meta.canonicalDoc` указывает на концепт |
| [DESIGN_PALETTE_PREMIUM_MANTINE.md](./DESIGN_PALETTE_PREMIUM_MANTINE.md) | Почему Mantine по умолчанию не равен премиуму; единый hue ink; критерии приёмки |
| [DESIGN_PALETTE_OPTIONS_PREMIUM_V1.md](./DESIGN_PALETTE_OPTIONS_PREMIUM_V1.md) | Сравнение направлений палитры; **канон — вариант 1 Swiss Slate / Ink** |
| [DESIGN_PALETTE_SPECTRUM_SWATCHES.html](./DESIGN_PALETTE_SPECTRUM_SWATCHES.html) | Полный спектр палитр (квадраты в браузере): §1 Swiss = канон; §2–5 — сравнение; блок Swiss — календарь |
| [DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html](./DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html) | Исследование «ожидает»; в проде — персиковый янтарь → `--calendar-scheduled-*` (см. HTML) |
| [DESIGN_COMPONENT_MAPPING.md](./DESIGN_COMPONENT_MAPPING.md) | Legacy к канону: ContextBar, Drawer/Modal, таблицы, формы, семантика |
| [DESIGN_CALENDAR_SEMANTIC_MAPPING.md](./DESIGN_CALENDAR_SEMANTIC_MAPPING.md) | Статусы расписания и `--calendar-*` |
| [DESIGN_SCHEDULE_MODAL_SEMANTICS_85_PLUS.md](./DESIGN_SCHEDULE_MODAL_SEMANTICS_85_PLUS.md) | Сетка слотов, модалка записи, иерархия кнопок |
| [DESIGN_P0_P1_BACKLOG.md](./DESIGN_P0_P1_BACKLOG.md) | Задачи DGN-P0/P1 с acceptance и owner |
| [DESIGN_SCREEN_AUDIT_MATRIX.csv](./DESIGN_SCREEN_AUDIT_MATRIX.csv) | Матрица экранов: модуль, finding, путь к коду |
| [LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md](./LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md) | Маршрут @LEAD: код и сопутствующие docs |
| [LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md](./LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md) | Пошаговое внедрение (token, shell, таблицы, drawer) |
| [LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md](./LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md) | ТЗ для дизайнера Enterprise 85+ |
| [REDISIGN_FRONT.md](./REDISIGN_FRONT.md) | Контекст редизайна фронта |
| [DESIGN_PASSPORT_MARKETING_LANDING.md](./DESIGN_PASSPORT_MARKETING_LANDING.md) | **Дизайн-паспорт** главной `/`: slate, типографика, секции, чеклист приёмки |

---

## Быстрый онбординг

1. [DESIGN_CODE_MAP.md](./DESIGN_CODE_MAP.md) — где в коде лежит тема и общие компоненты.
2. Executive summary и **§3.6** в [DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md](./DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md).
3. Палитра в браузере: [DESIGN_PALETTE_SPECTRUM_SWATCHES.html](./DESIGN_PALETTE_SPECTRUM_SWATCHES.html) (§1 Swiss + календарь); слот pending — [DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html](./DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html).
4. Правки UI сверять с [DESIGN_TOKENS_85_PLUS.json](./DESIGN_TOKENS_85_PLUS.json) и [DESIGN_COMPONENT_MAPPING.md](./DESIGN_COMPONENT_MAPPING.md).

---

## Связь с репозиторием

- [docs/ROLE_DESIGN.md](../ROLE_DESIGN.md)
- [docs/TEMPLATE_ADMIN_UI_UX.md](../TEMPLATE_ADMIN_UI_UX.md)
- [docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md)

**Индекс:** 2026-04-10 — канон в `docs/design/`; **DESIGN_CODE_MAP.md** (дизайн ↔ код). HTML-свотчи — полноразмерные референсы (открыть локально в браузере).
