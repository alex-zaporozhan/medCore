# Публичная документация репозитория

> **Версия:** 2026-04-02  
> **Назначение:** всё, что **можно** отдавать в git, клиентам и покупателям. Здесь нет внутренних регламентов команд и путей к закрытым материалам.

**Официальный порядок и слои:** [STRUCTURE.md](./STRUCTURE.md). Политика репозитория: **`DOCUMENTATION_POLICY.md`** (корень проекта).

### Журнал согласований (фрагмент)

| Дата | Что зафиксировано |
|------|-------------------|
| 2026-04-02 | Проход **@QA_ARCH:** уточнён канон `ALL_PUBLIC_APP_PATHS` vs динамические маршруты (KB §5.4); исправлено описание PWA «Профиль»; питч привязан к KB §5; добавлены `PATIENT_OAUTH_RESULT`, `PUBLIC_DOCTOR_PROFILE`; в INDEX — явный объём v1. |
| 2026-04-02 | Проход **@LEAD:** `API_V1_ROUTER_MANIFEST.md` (78 модулей из `router.py`); `LEAD_DOC_AUDIT.md` (границы «100% из кода»); `ADMIN_DASHBOARD.md` переписан по фактическому `AdminDashboardPage.tsx`. |
| 2026-04-02 | Проход **@LEAD (роутеры):** `scripts/generate_router_surface_docs.py` + `router_surface/INDEX.md`; feature-доки Kanban/чаты/календарь/оплаты; `TESTING_SURFACE.md`; `SCRIBE_ROUTER_CHECKLIST.md` и обновление `SCRIBE.md`. |

## С чего начать

| Файл | Содержание |
|------|------------|
| [STRUCTURE.md](./STRUCTURE.md) | Порядок файлов, RAG без дублей, уровни «продукт / техника / процесс» |
| [PRODUCT_OVERVIEW.md](./PRODUCT_OVERVIEW.md) | Кратко о продукте и репозитории |
| [PRODUCT_KNOWLEDGE_BASE.md](./PRODUCT_KNOWLEDGE_BASE.md) | База знаний о продукте (канон для поддержки и RAG по git) |
| [SALES_PITCH.md](./SALES_PITCH.md) | Короткий B2B-питч |
| [PROJECT_REPOSITORY_LAYOUT.md](./PROJECT_REPOSITORY_LAYOUT.md) | Дерево каталогов репозитория |
| [USER_DOCS/INDEX.md](./USER_DOCS/INDEX.md) | Оглавление пользовательских гайдов |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Запуск, порты, тестовая БД, миграции |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Алерты, Grafana, где смотреть пороги в репозитории |
| [UI_THEME.md](./UI_THEME.md) | Тема админки (Swiss Slate / Ink), ориентиры для фронта |
| [E2E_TESTING.md](./E2E_TESTING.md) | Playwright / smoke-маршруты |
| [API_V1_ROUTER_MANIFEST.md](./API_V1_ROUTER_MANIFEST.md) | Порядок и префиксы всех роутеров v1 (из кода) |
| [router_surface/INDEX.md](./router_surface/INDEX.md) | Автосводка по каждому роутеру: HTTP-пути, метрики, pytest |
| [SCRIBE_ROUTER_CHECKLIST.md](./SCRIBE_ROUTER_CHECKLIST.md) | Обязательный порядок работы документатора по 78 модулям |
| [TESTING_SURFACE.md](./TESTING_SURFACE.md) | Где лежат тесты и как связать с API |
| [FEATURE_KANBAN_AND_TASKS.md](./FEATURE_KANBAN_AND_TASKS.md) · [FEATURE_CHATS_OMNI_PATIENT_STAFF.md](./FEATURE_CHATS_OMNI_PATIENT_STAFF.md) · [FEATURE_CALENDAR_SCHEDULE.md](./FEATURE_CALENDAR_SCHEDULE.md) · [FEATURE_PAYMENTS_FINANCE.md](./FEATURE_PAYMENTS_FINANCE.md) | Сквозные продуктовые зоны поверх роутеров |
| [LEAD_DOC_AUDIT.md](./LEAD_DOC_AUDIT.md) | Аудит @LEAD: границы канона, бэклог |
| [SCRIBE.md](./SCRIBE.md) | Куда писать пользовательскую и продуктовую документацию (**обязательно к прочтению для роли документатора**) |
| [rbac_router_permissions.txt](./rbac_router_permissions.txt) | Снимок кодов прав `require_permissions` (для аудита и CI) |
| [RBAC_RIGHTS_POLICIES_GUIDE.md](./RBAC_RIGHTS_POLICIES_GUIDE.md) · [RBAC_RIGHTS_POLICIES_GUIDE.en.md](./RBAC_RIGHTS_POLICIES_GUIDE.en.md) | Права и политики для пользователей продукта |

Пользовательские гайды для конечных пользователей — каталог [`USER_DOCS/`](./USER_DOCS/), оглавление — [USER_DOCS/INDEX.md](./USER_DOCS/INDEX.md) (файлы по модулям добавляются по мере готовности).

---

## Внутренняя документация и RAG

Рабочие материалы команды (роли, эпики, закрытые паспорта, корпус для корпоративного RAG) **не входят** в этот репозиторий и **не описыются** в файлах под `documentation/`. Они ведутся отдельно по регламенту организации.

---

Reference: корневой `README.md`, `CONTRIBUTING.md`, `DOCUMENTATION_POLICY.md`
