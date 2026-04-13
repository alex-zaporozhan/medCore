# LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS — ТЗ для @DESIGNER

> **Роль постановщика:** @LEAD  
> **Исполнитель:** @DESIGNER  
> **Цель:** провести полный UI/UX аудит и сформировать единый enterprise-дизайн-концепт в логике 85+ (`quality by evidence`, не “косметика”).  
> **Результат:** один консистентный дизайн-стандарт + карта внедрения по всем экранам.  
> **Каталог:** артефакты `DESIGN_*` ниже лежат в **`docs/design/`** (индекс — [README.md](./README.md)).

---

## 1) Контекст и ожидание уровня 85+

Для 85+ дизайн должен подтверждать:

1. единый визуальный язык во всех модулях (Admin, CRM, Tasks, Omni, Reports, Schedule),
2. предсказуемое поведение UI в норме/ошибках/деградации,
3. доступность и читабельность на enterprise-нагрузке,
4. масштабируемость дизайн-системы без расползания стилей.

Ключевой принцип: **каждое замечание подтверждается evidence (скрин, компонент, сценарий, риск)**.

---

## 2) Область аудита (обязательно)

`@DESIGNER` должен проанализировать **каждую страницу и ключевые интерфейсы**, включая:

1. авторизация и entry points,
2. dashboard/аналитика,
3. календарь/расписание/слоты,
4. CRM/pipeline/карточки лидов,
5. tasks/workstation/kanban,
6. omnichannel/chat/attention feed,
7. отчёты/финансы/ERP-витрины,
8. формы создания/редактирования/подтверждения,
9. drawers/modals/popovers/tooltips,
10. таблицы, фильтры, пагинация, bulk actions,
11. empty/loading/error/skeleton states,
12. mobile/tablet critical screens (если есть),
13. box vs enterprise edition UX-различия.

---

## 3) Что проверить по каждой странице (чеклист)

Для **каждой** страницы/экрана заполнить карточку аудита:

1. **Structure**
   - иерархия контента, плотность, visual balance, приоритеты блоков.
2. **Typography**
   - шкала размеров, line-height, веса, контраст, читаемость длинных таблиц/форм.
3. **Color system**
   - primary/neutral/semantic палитра (**канон Enterprise 85+:** Swiss Slate / Ink — `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6), контраст WCAG, consistency статусов.
4. **Elevation & shadows**
   - уровни глубины, единая логика карточек/модалок/drawer.
5. **Spacing & grid**
   - ритм отступов, alignment, сетка, адаптивные брейкпоинты.
6. **Controls**
   - кнопки, инпуты, селекты, чекбоксы, переключатели, date/time элементы.
7. **State model**
   - hover/focus/active/disabled/loading/error/success.
8. **Feedback**
   - toast/inline errors/helper text/confirmation patterns.
9. **Data-heavy UX**
   - таблицы, фильтры, сортировки, sticky headers, scanability.
10. **Accessibility**
   - keyboard flow, focus order, contrast, target sizes, screen-reader semantics.
11. **Edition integrity**
   - UX для Box/Enterprise: отсутствие “мертвых” переходов и скрытых ловушек.
12. **Design debt**
   - дубли компонент, конфликтные паттерны, legacy-style участки.

---

## 4) Формат итогового документа (обязательный)

`@DESIGNER` должен сдать единый документ:

- `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`

Структура документа:

1. **Executive summary**
   - текущий уровень зрелости UI (оценка 0..10),
   - top-10 критичных проблем (с приоритетом).
2. **Screen inventory**
   - список всех экранов с группировкой по модулям.
3. **Audit matrix per screen**
   - экран -> finding -> severity -> evidence -> recommendation.
4. **Unified design system spec**
   - токены, типографика, цветовые роли, тени, радиусы, spacing scale.
5. **Component standardization**
   - canonical patterns для table/form/card/drawer/modal/chat/pipeline.
6. **State & feedback model**
   - единые правила для loading/error/empty/partial failure.
7. **Accessibility baseline**
   - минимум WCAG 2.1 AA для admin-контура.
8. **Edition UX policy**
   - отдельные правила Box vs Enterprise на уровне интерфейса.
9. **Prioritized redesign roadmap**
   - P0/P1/P2 c effort и зависимостями.
10. **Definition of Done (Design)**
   - критерии приёмки перед handoff в DEV.

---

## 5) Severity и приоритизация находок

| Severity | Критерий | Ожидаемое действие |
|---------|----------|--------------------|
| P0 | UX ломает сценарий/доверие к данным/ошибка в критичном потоке | блокер релиза UX |
| P1 | Значимое ухудшение эффективности работы персонала | фикс в ближайшем цикле |
| P2 | Консистентность/эстетика/долг без прямого блокера | плановый рефактор |

---

## 6) Design tokens и система (что обязательно определить)

1. **Typography tokens**
   - font family, scale (например 12/14/16/20/24...), weights, line heights.
2. **Color tokens**
   - neutral scale, brand scale, semantic success/warning/error/info.
3. **Shadow/elevation tokens**
   - минимум 4-6 уровней с явным применением.
4. **Spacing/radius tokens**
   - единая шкала отступов и скруглений.
5. **Motion tokens (минимум)**
   - duration/easing для типовых переходов.
6. **Interaction tokens**
   - focus ring, border states, disabled opacity.

Все токены должны быть подготовлены для переноса в frontend theme/design system.

---

## 7) Артефакты, которые обязан передать @DESIGNER

1. `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` (основной документ),
2. `DESIGN_SCREEN_AUDIT_MATRIX.csv` (табличный аудит по экранам),
3. `DESIGN_TOKENS_85_PLUS.json` (или эквивалентная таблица),
4. `DESIGN_COMPONENT_MAPPING.md` (legacy -> canonical component map),
5. `DESIGN_P0_P1_BACKLOG.md` (задачи для внедрения).

---

## 8) DoD для @DESIGNER (строгий)

Задача считается выполненной, если:

1. покрыты все экраны из screen inventory (без “неуспели”),
2. у каждого finding есть severity и evidence,
3. есть единая token-система и component rules,
4. есть roadmap внедрения с P0/P1/P2,
5. документ проверяем и применим командой DEV без доп. догадок.

---

## 9) Таймлайн (рекомендуемый)

1. **День 1-2:** inventory + первичный аудит,
2. **День 3-4:** unified concept + design tokens,
3. **День 5:** component mapping + backlog + финальный пакет.

---

## 10) Критерий приёмки от @LEAD

Приёмка проходит только если:

1. концепция устраняет ключевые противоречия интерфейсов,
2. нет конфликтов между модулями по типографике/цветам/теням/состояниям,
3. есть чёткая связь с execution-контурами 85+ (P0/P1/P2, evidence, DoD),
4. результат готов к непосредственной декомпозиции в задачи для DEV.
