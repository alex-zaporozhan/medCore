"""One-off: write docs/architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md (UTF-8)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture" / "ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md"

BODY = r"""# Рубрика «продающего» фронтенда Enterprise SaaS и итерации приёмки

> **Версия:** 2026-04-08
> **Назначение:** многоосевые критерии оценки макро- и микроуровня UI (оболочка продукта vs экран), стандарты для рабочего контура (`/admin`, `/app`, `/platform`) и витрины (`/`, `/pricing`, `/signup`), методология нескольких итераций аудита.
> **Дополняет:** [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) (платформа и эксплуатация); здесь — продуктовый UI, доверие покупателя, связь с API.

**Трассируемость:** утверждение «готово для Enterprise» по UI — с якорем: файл во `frontend/src/`, запись сети, или пометка «не подтверждено».

---

## 1. Корпус документов

| Слой | Документ |
|------|-----------|
| Факты | [../product_state/FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md) |
| Поведение экранов | [../TECH_PASSPORT_FRONTEND_UI_LOGIC.md](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md) |
| Тема и токены | [../ARCH_FRONTEND_UI_LOGIC.md](../ARCH_FRONTEND_UI_LOGIC.md), `frontend/src/theme.ts` |
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

**Красные флаги:** нет запросов в типичном сценарии; кнопка без мутации; статический список вместо API; документированный эндпоинт не вызывается с фронта.

Итог матрицы — вход для QA и для [arch_plan/STREAM_FRONTEND_SAAS_EPICS.md](./arch_plan/STREAM_FRONTEND_SAAS_EPICS.md).

---

## 7. Итерации аудита (A / B / C)

- **A — Discovery:** покрытие маршрутов, факт вызовов API, явные заглушки. Выход: таблица маршрут ↔ API; список P0 «нет запросов».
- **B — Strict:** микро-оси, DOMAIN_STANDARDS по типу страницы; оценки 0/1/2 по осям.
- **C — Buyer simulation:** макро-оси и §5; сценарий «покупаю за сеть клиник»; вердикт go/no-go.

Между итерациями обновлять паспорта фактами и ссылками на этот документ, без дублирования полного чеклиста в каждом файле.

---

## 8. Красные флаги фронтенда (стоп для формулировки «Enterprise UI»)

1. Операционный экран без вызова API в штатном сценарии.
2. Кнопки сохранения без эффекта или без обработки ошибки.
3. UUID в таблице вместо имён, где бэкенд отдаёт человекочитаемые поля.
4. Интеграционная страница без полей секретов и без проверки подключения.
5. Расхождение `VITE_EDITION` и бэкенд `EDITION`.
6. Stack trace или сырой JSON ошибки в публичной сборке.

---

## 9. Связанные документы

- [../product_state/FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md)
- [../ROLE_FRONTEND.md](../ROLE_FRONTEND.md)
- [./ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) — при полном аудите фиксировать разрыв «бэкенд зрелее фронта».

**Якорные файлы кода:** `frontend/src/App.tsx`, `frontend/src/routePaths.ts`, `frontend/src/api/client.ts`, `frontend/src/config/edition.ts`, `frontend/src/admin/pages/`, `frontend/src/app/pages/`.
"""

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(BODY.strip() + "\n", encoding="utf-8")
    print("Wrote", OUT)
