# Календарь админки: семантика цвета (Swiss)

**Источник визуала:**

- `docs/design/DESIGN_PALETTE_SPECTRUM_SWATCHES.html` — секция **«Swiss — календарь»** (все `--calendar-*` на одном экране).
- `docs/design/DESIGN_PENDING_SLOT_PALETTE_OPTIONS.html` — почему для **pending / «Занято»** выбран **персиковый янтарь** (опция H), а не чистый жёлтый; карточки-превью.

**Токены в коде:** `frontend/src/index.css` — `var(--calendar-*)`; JSON: `docs/design/DESIGN_TOKENS_85_PLUS.json` → `color.calendar`.

## Принцип (меньше «серых карточек»)

- **Ожидает (`pending`)** — **персиковый янтарь** (`--calendar-scheduled-*`): тёплая слоновая кость, полоска orange-600, бейдж персик; текст бейджа ink, не коричневый.
- **Подтверждено (`confirmed`)** — **denim** (`--calendar-attention-denim-*`): спокойный зафиксированный визит, не сливается с жёлтым ожиданием.
- **Fallback «Занято»** (нет явного статуса) — та же палитра **персиковый янтарь**, что и `pending`.
- **На приёме (`in_progress`)** — **изумруд** (`--calendar-in-progress-*`).
- **Завершено** — архив **ink** (`--calendar-completed-*`), отдельно от зелёного приёма.
- **Отмена / неявка** — вишня (`--calendar-negative-*`).
- **Коралл** (`--calendar-attention-coral-*`) — в календаре врача для записей **не используем**; оставлен для **событий персонала** («новое для меня»).

## Записи врача (`ScheduleCalendarGrid` → `SchedulePage`, маршрут `schedule`)

| Статус брони | Токены | Смысл |
|--------------|--------|--------|
| `pending` | `scheduled` | Ожидает — персиковый янтарь |
| `confirmed` | `attention-denim` | Подтверждено — slate-denim |
| fallback «Занято» | `scheduled` | Занят слот без статуса — персиковый янтарь |
| `completed` | `completed` | Архив / ink |
| `in_progress` | `in-progress` | На приёме — зелёный |
| `cancelled`, `no_show` | `negative` | Потеря слота |

## События персонала (`AdminStaffCalendarPage`)

| Условие | Токены | Смысл |
|---------|--------|--------|
| Непросмотрено (`isUnseen`) | `attention-coral` | «Новое для меня», ждёт реакции |
| Напоминание (`isReminder`) | `scheduled` | Время/напоминание — тот же персиковый янтарь |
| Обычное событие | `attention-denim` | Спокойное, не белое полотно |

## Внедрение

- Палитра слотов: только `--calendar-*` в компонентах; hex не дублировать.
- Тосты/формы: `--success` / `--warning` / `--danger` (§3.6.2a) — отдельно от календаря.
