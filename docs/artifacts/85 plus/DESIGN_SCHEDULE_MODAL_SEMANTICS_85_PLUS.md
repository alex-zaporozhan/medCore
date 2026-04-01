# DESIGN_SCHEDULE_MODAL_SEMANTICS_85_PLUS

> **Роль:** @DESIGN  
> **Связь:** `DESIGN_TOKENS_85_PLUS.json`, `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md` (Step 4), `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6  
> **Статус:** принято к реализации в коде (`ScheduleCalendarGrid`, `index.css` `--calendar-*`, `BookingEntityDrawer`, `entityDrawerChrome`).

---

## 1. Расписание: единый каркас + смысловая семантика

### 1.1 Принципы

1. **Один каркас слота** для всех статусов: одинаковые скругление (`--calendar-slot-radius`), мягкая тень и тонкая обводка (`--calendar-card-shadow`, `--calendar-card-border`), внутренние отступы.
2. **Смысл** передаёт **левая полоса** (`--calendar-bar-width`) + **бейдж** + **лёгкий тон фона** из канона `--calendar-*` — без «разных типов карточек».
3. **Типографика:** ФИО пациента — `fw 600`, услуга — `fw 500` на второй строке; цвета текста из `--calendar-*-title` / `-meta`.
4. **Навигация:** заголовок колонки врача и ФИО в ячейке — ссылки на карточки (`/admin/doctors?…`, `/admin/patients?…`) с `stopPropagation` на клике по ссылке в ячейке, чтобы не открывать модалку записи.

### 1.2 Токены (источник правды)

- Переменные в `frontend/src/index.css` (`:root`): `--calendar-completed-*`, `--calendar-scheduled-*`, `--calendar-in-progress-*`, `--calendar-attention-denim-*`, `--calendar-negative-*`, и т.д.
- Дополнительно для единства хрома слота: `--calendar-card-border`, `--calendar-card-shadow`.
- Паритет в JSON: `DESIGN_TOKENS_85_PLUS.json` → `color.calendar.cardBorder`, `cardShadow`, а также `cssVarCardBorder` / `cssVarCardShadow` (имена CSS-переменных).

### 1.3 Палитра статусов (кратко)

| Смысл        | Ключ в коде   | Фон / акцент                          |
|-------------|---------------|----------------------------------------|
| Завершён    | `completed`   | нейтраль surface + ink bar             |
| На приёме   | `in_progress` | изумрудный тон                         |
| Ожидает     | `pending`       | персиковый янтарь (scheduled)          |
| Подтверждён | `confirmed`     | denim-тон                              |
| Неявка / отмена | `no_show` / `cancelled` | negative plum/coral |

Подробная семантика — `DESIGN_CALENDAR_SEMANTIC_MAPPING.md` (если есть) и свотчи в `DESIGN_PALETTE_SPECTRUM_SWATCHES.html`.

---

## 2. Модалка «Запись»: поля и кнопки

### 2.1 Поля (field blocks)

- Фон **светлее серого блока**: по сути **белый** с тонкой границей `gray.1` и микротенью — чтобы блок не читался как «вторая кнопка».
- Компонент: `EntityDrawerFieldBlock` в `entityDrawerChrome.tsx`.

### 2.2 Иерархия кнопок (один primary на экране)

| Действие                     | Роль        | Визуал                                      |
|-----------------------------|-------------|---------------------------------------------|
| Сохранить комментарий       | Primary     | `filled` + `color="brand"` (при наличии изменений) |
| Скопировать ссылку посещения | Secondary   | `outline` + `color="brand"`                 |
| Изменить дату / время / врача | Tertiary    | `outline` + иконка календаря                |
| Отменить запись             | Destructive | `subtle` или `light` + `color="red"`        |
| Сохранить (режим редактирования) | Primary | `filled` + `brand`                          |
| Отмена (режим редактирования)   | Dismiss | `outline` / `light` + `gray`                |

---

## 3. Evidence / приёмка

- Визуальный smoke: расписание — все слоты с записью имеют одинаковую «рамку» (тень + бордер), различаются полоса/бейдж/фон.
- Модалка: поля визуально светлее кнопок; одна primary-действие очевидна.
- Клики по ФИО врача в шапке и по пациенту в ячейке ведут на нужные маршруты без открытия модалки записи при клике по ссылке.

---

## 4. История изменений

| Дата       | Изменение |
|------------|-----------|
| 2026-03-27 | Первая версия: семантика сетки + модалка + иерархия кнопок; реализация в коде. |
