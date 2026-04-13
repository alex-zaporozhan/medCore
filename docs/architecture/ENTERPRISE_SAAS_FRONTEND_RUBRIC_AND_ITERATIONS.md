# Рубрика «продающего» фронтенда Enterprise SaaS и итерации приёмки

> **Версия:** 2026-04-10  
> **Назначение:** многоосевые критерии оценки макро- и микроуровня UI (оболочка продукта vs экран), стандарты для рабочего контура (`/admin`, `/app`, `/platform`) и витрины (`/`, `/pricing`, `/signup`), методология нескольких итераций аудита.  
> **Дополняет:** [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) (платформа и эксплуатация); здесь — продуктовый UI, доверие покупателя, связь с API.

**Трассируемость:** утверждение «готово для Enterprise» по UI — с якорем: файл во `frontend/src/`, запись сети, или пометка «не подтверждено».

**Единая точка входа по зонам SPA, данным и компонентным правилам (этот репозиторий):** [../frontend/FRONTEND_ARCHITECTURE_CANON.md](../frontend/FRONTEND_ARCHITECTURE_CANON.md). Слои и трассируемость кода: [../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md). Критерии пер-страничного паспорта (в т.ч. **инвентарь drawer/modal/menu** — ось H): [../frontend/PAGE_PASSPORT_CRITERIA.md](../frontend/PAGE_PASSPORT_CRITERIA.md); каталог паспортов: [../frontend/pages/README.md](../frontend/pages/README.md).

---

## 1. Корпус документов

| Слой | Документ |
|------|-----------|
| Факты | [../product_state/FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md) |
| Канон зон / данные / drawer | [../frontend/FRONTEND_ARCHITECTURE_CANON.md](../frontend/FRONTEND_ARCHITECTURE_CANON.md) |
| Слои SPA, PR-чеклист, проверяемость | [../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md) |
| Поведение экранов | [../TECH_PASSPORT_FRONTEND_UI_LOGIC.md](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md) |
| Тема и токены | [../frontend/UI_THEME.md](../frontend/UI_THEME.md), [../ARCH_FRONTEND_UI_LOGIC.md](../ARCH_FRONTEND_UI_LOGIC.md), `frontend/src/theme.ts` |
| Витрина | [../TEMPLATE_DESIGN_UX.md](../TEMPLATE_DESIGN_UX.md) |
| Админ DoD | [../TEMPLATE_ADMIN_UI_UX.md](../TEMPLATE_ADMIN_UI_UX.md) |
| Домен | [../DOMAIN_STANDARDS.md](../DOMAIN_STANDARDS.md) |
| Дизайн 85+ | [../design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md](../design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md), [../design/DESIGN_TOKENS_85_PLUS.json](../design/DESIGN_TOKENS_85_PLUS.json) |
| Внедрение | [../design/LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md](../design/LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md), [../design/DESIGN_COMPONENT_MAPPING.md](../design/DESIGN_COMPONENT_MAPPING.md) |
| Срезы FE | [arch_plan/STREAM_FRONTEND_SAAS_EPICS.md](./arch_plan/STREAM_FRONTEND_SAAS_EPICS.md) |
| Роль | [../ROLE_FRONTEND.md](../ROLE_FRONTEND.md) |

Сверять код, паспорта и `docs/design/`; расхождения — в [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).

---

## 2. Шкала по оси UI

| Уровень | Смысл |
|---------|--------|
| **0** | Нет целевого действия; кнопки без эффекта; маршрут без данных. |
| **1** | Данные частично; неполные состояния или API; визуал без иерархии §7 техпаспорта. |
| **2** | Сквозной сценарий; Loading/Empty/Error/Success; контекстные действия; трассировка к API. |

---

## 3. Макро-оси

| ID | Ось | Проверка |
|----|-----|-----------|
| M1 | Информационная архитектура | Sidebar, группы; сегменты = `ADMIN_SHELL_ROUTE_SEGMENTS` в `frontend/src/routePaths.ts`. |
| M2 | Доверие и бренд | Тон текстов; нет внутренних кодов в UI; юридические страницы на витрине. |
| M3 | Сквозной контур | Список → Drawer/карточка → действие; Spotlight по мере данных. |
| M4 | Гейты | Entitlement, RBAC; Box vs Enterprise — `frontend/src/config/edition.ts` и бэкенд `EDITION`. |
| M5 | Два контура | Витрина не смешана с операционным UI (ROLE_FRONTEND). |
| M6 | Платформа | `/platform/*`, login/MFA, состояния. |
| M7 | Ошибки для пользователя | Понятный текст; `X-Request-Id`; нет stack trace в prod. |

---

## 4. Микро-оси

| ID | Ось | Проверка | Норма |
|----|-----|-----------|--------|
| μ1 | Иерархия | Фон/карточки/тени; без глобального скролла-лендинга на операционных экранах. | TECH_PASSPORT §7, §9.1 |
| μ2 | Типографика | Плотность таблиц; контраст. | §7.4–7.5 |
| μ3 | Состояния | Skeleton, Empty+CTA, Error. | DOMAIN_STANDARDS |
| μ4 | Контекст | Меню строки; вкладки сущности. | TECH_PASSPORT §3–4 |
| μ5 | Модальность | Drawer для данных; Modal — confirm. | TECH_PASSPORT §1 |
| μ6 | Эффекты | По техпаспорту; blur витрины не на таблицы без @ARCH. | TEMPLATE_DESIGN_UX |
| μ7 | Ввод | Фокус; хоткеи Omni — в техпаспорте. | Код страницы |

---

## 5. Деловой лайв-контекст

**Глобально:** единые сущности и переходы; фильтры/экспорт где есть API; доменные тексты без пустых блоков.

**На странице:** заголовок задаёт цель; одно первичное действие; таблица с фильтрами/пагинацией при реалистичном объёме; интеграции — поля секретов и проверка подключения (см. [../ROLE_FRONTEND.md](../ROLE_FRONTEND.md), п.13 про заглушки).

---

## 6. Матрица UI ↔ API

Для каждого смыслового экрана: маршрут, назначение, HTTP-методы (префикс `/api/`), хук или модуль фронта, статус (полный контур / только чтение / не подключено). Сверка с [../product_state/BACKEND_PASSPORT.md](../product_state/BACKEND_PASSPORT.md) и деревом `src/api/v1/routers/`.

**Как сверять эндпоинты с фронтом (практика):**

- Сводный манифест HTTP: [`../../documentation/API_V1_ROUTER_MANIFEST.md`](../../documentation/API_V1_ROUTER_MANIFEST.md) (при переносе в `docs/` — обновить путь на `../API_V1_ROUTER_MANIFEST.md`); узкие срезы: `documentation/router_surface/` при наличии.
- По коду: поиск `api.get` / `api.post` / `useQuery` в `frontend/src/hooks/` и страницах под `frontend/src/admin/pages/`, `frontend/src/app/pages/`.

**Красные флаги:** нет запросов в типичном сценарии; кнопка без мутации; статический список вместо API; документированный эндпоинт не вызывается с фронта.

**Сквозная проверка «покупатель» (обязательная цепочка):** маршрут → хук(и) → HTTP → состояния Loading / Empty / Error → ожидаемый результат первичного действия (кнопка, сохранение, фильтр). Без этой цепочки высокая оценка по §2 недостижима.

Итог матрицы — вход для QA и для [arch_plan/STREAM_FRONTEND_SAAS_EPICS.md](./arch_plan/STREAM_FRONTEND_SAAS_EPICS.md). Рабочий перечень маршрутов для построчного аудита: [../review/FRONTEND_ROUTE_AUDIT_MATRIX.md](../review/FRONTEND_ROUTE_AUDIT_MATRIX.md).

Тексты в UI (RU): [../COPY_STYLE_POLICY_RU.md](../COPY_STYLE_POLICY_RU.md).

---

## 7. Итерации аудита (A / B / C)

- **A — Discovery:** покрытие маршрутов, факт вызовов API, явные заглушки. Выход: таблица маршрут ↔ API; список P0 «нет запросов».
- **B — Strict:** микро-оси, DOMAIN_STANDARDS по типу страницы; оценки 0/1/2 по осям.
- **C — Buyer simulation:** макро-оси и §5; сценарий «покупаю за сеть клиник»; вердикт go/no-go.

Между итерациями обновлять паспорта фактами и ссылками на этот документ, без дублирования полного чеклиста в каждом файле.

---

## 8. Кейс: Payroll / Finance (`/admin/finance`) — анти-паттерн и исправление

**Симптом:** пустой селект врача при просмотре зарплат, хотя в клинике есть врачи.

**Корневая причина (два слоя):**

1. **Запрос зарплат** был включён в React Query только при уже выбранном `doctor_id` (`enabled: !!doctorId`), тогда как для агрегатов и первичной загрузки нужен список транзакций по клинике без фильтра по врачу.
2. **Опции селекта** строились из уже загруженных salary-транзакций (уникальные `doctor_id`), а не из справочника врачей — при отсутствии начислений список оставался пустым (логический тупик).

**Правило приёмки:** источник опций для селекта сущности (врач, пациент, касса и т.д.) — **соответствующий справочный API** (например `GET /v1/doctors` через `useDoctors`), а не производные от зависимого списка, который сам требует выбора из этого селекта.

**Исправление в коде (ориентиры):** опциональный query `doctor_id` на `GET /api/v1/admin/clinics/{id}/payroll/transactions`; на фронте — `useDoctors` для данных селекта и `enabled: !!clinicId` для списка транзакций. Имена в таблицах — через мапу `doctor_id → full_name`, а не сырой UUID.

**Связь с дизайном:** визуал карточек/таблиц на экране не менялся; исправление — **контракт данных и состояния**. Любое изменение токенов/теней для Finance должно проходить ту же сквозную линию, что и в [../frontend/UI_THEME.md](../frontend/UI_THEME.md) и [../design/](../design/).

---

## 9. Красные флаги фронтенда (стоп для формулировки «Enterprise UI»)

1. Операционный экран без вызова API в штатном сценарии.
2. Кнопки сохранения без эффекта или без обработки ошибки.
3. UUID в таблице вместо имён, где бэкенд отдаёт человекочитаемые поля.
4. Интеграционная страница без полей секретов и без проверки подключения.
5. Расхождение `VITE_EDITION` и бэкенд `EDITION`.
6. Stack trace или сырой JSON ошибки в публичной сборке.
7. Селект, заполняемый только из ответа зависимого запроса, который сам не выполняется без выбора в селекте (см. §8).

---

## 10. Связанные документы

- [../product_state/FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md)
- [../ROLE_FRONTEND.md](../ROLE_FRONTEND.md)
- [./ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) — при полном аудите фиксировать разрыв «бэкенд зрелее фронта».

**Якорные файлы кода:** `frontend/src/App.tsx`, `frontend/src/routePaths.ts`, `frontend/src/api/client.ts`, `frontend/src/config/edition.ts`, `frontend/src/admin/pages/`, `frontend/src/app/pages/`.
