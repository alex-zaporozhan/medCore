# Официальная структура `documentation/`

> **Версия:** 2026-04-02  
> **Назначение:** единый порядок файлов для команды, покупателей и RAG по **публичному** репозиторию. Дубликаты смысла между «для клиента» и «для RAG» **не ведём**: один и тот же файл в `documentation/` обслуживает и людей, и индексацию, если содержание безопасно для внешней аудитории.

---

## Уровень 1 — продукт и пользователи (приоритет для онбординга и продаж)

| Порядок | Путь | Назначение |
|--------:|------|-------------|
| 1 | [README.md](./README.md) | Вход, оглавление |
| 2 | [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md) | Что за продукт одним экраном |
| 3 | [SALES_PITCH.md](./SALES_PITCH.md) | Короткий питч для B2B |
| 4 | [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) | База знаний о продукте: **канон для поддержки, клиентского RAG и чтения из git** |
| 5 | [USER_DOCS/](./USER_DOCS/) | End-user гайды; оглавление — [USER_DOCS/INDEX.md](./USER_DOCS/INDEX.md) |

Всё перечисленное должно быть **согласовано с кодом**; противоречие коду — баг документации.

---

## Уровень 2 — интеграция и эксплуатация (техническая публичная зона)

| Порядок | Путь | Назначение |
|--------:|------|-------------|
| 6 | [DEVELOPMENT.md](./DEVELOPMENT.md) | Запуск, порты, тестовая БД |
| 7 | [OBSERVABILITY.md](./OBSERVABILITY.md) | Prometheus/Grafana в репозитории |
| 8 | [E2E_TESTING.md](./E2E_TESTING.md) | Playwright |
| 9 | [UI_THEME.md](./UI_THEME.md) | Публичные ориентиры темы UI |
| 10 | [RBAC_RIGHTS_POLICIES_GUIDE.md](./RBAC_RIGHTS_POLICIES_GUIDE.md) (+ `.en.md`) | Права для пользователей продукта |
| 11 | [rbac_router_permissions.txt](./rbac_router_permissions.txt) | Машиночитаемый список кодов прав (CI/аудит) |
| 12 | [PROJECT_REPOSITORY_LAYOUT.md](./PROJECT_REPOSITORY_LAYOUT.md) | Дерево каталогов для разработчиков и интеграторов |
| 13 | [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md) | Порядок подключения роутеров v1 (префиксы) |
| 14 | [router_surface/INDEX.md](./router_surface/INDEX.md) | Автосводка по каждому роутеру: пути, метрики, pytest |
| 15 | [TESTING_SURFACE.md](./TESTING_SURFACE.md) | Где лежат тесты и как связать с роутерами |
| 16 | [FEATURE_KANBAN_AND_TASKS.md](./FEATURE_KANBAN_AND_TASKS.md) | Kanban, задачи, доски, потоки, теги |
| 17 | [FEATURE_CHATS_OMNI_PATIENT_STAFF.md](./FEATURE_CHATS_OMNI_PATIENT_STAFF.md) | Омни, чат пациента, staff-chat, admin chat |
| 18 | [FEATURE_CALENDAR_SCHEDULE.md](./FEATURE_CALENDAR_SCHEDULE.md) | Расписание и календари |
| 19 | [FEATURE_PAYMENTS_FINANCE.md](./FEATURE_PAYMENTS_FINANCE.md) | Платежи, шлюз, финансы |
| 20 | [LEAD_DOC_AUDIT.md](./LEAD_DOC_AUDIT.md) | Аудит полноты документации и бэклог |
| 21 | `openapi.json` | Снимок API, если публикуете (опционально) |

---

## Уровень 3 — процесс публикации текстов

| Путь | Назначение |
|------|------------|
| [SCRIBE.md](./SCRIBE.md) | Где создавать материалы уровня 1–2; **чек-лист роутеров** — [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md) |
| [STRUCTURE.md](./STRUCTURE.md) | Этот файл — контракт структуры |

---

## RAG: один источник без дублирования

- **Публичный RAG** (индекс только git): уровни 1–2 + исходный код + тесты.  
- **Расширенный внутренний RAG** команды: публичный индекс **плюс** закрытые материалы вне репозитория. Туда **не копировать** дословно `PRODUCT_KNOWLEDGE_BASE.md` / `USER_DOCS/*` — на них **ссылаются** как на канон в git; в закрытом слое держать только процессы, решения @LEAD, черновики волн, то что нельзя показать клиенту.

---

Reference: [README.md](./README.md) · корневой `DOCUMENTATION_POLICY.md`
