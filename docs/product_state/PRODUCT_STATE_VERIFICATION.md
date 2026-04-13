# Слой S: сверка паспортов с кодом (@QA_ARCH)

> **Версия:** 2026-04-10  
> **Назначение:** регламент проверки **содержания** `docs/product_state/*.md`, а не только ссылок. Числа в паспортах устаревают при росте репозитория — этот файл задаёт, что пересчитывать.

---

## 1. Приоритет истины

1. Исходный код и тесты (`src/`, `frontend/src/`, `tests/`, `alembic/versions/`).  
2. Документы слоя S в `docs/product_state/`.  
3. Остальной `docs/` (процесс, слой W в `docs/artifacts/` — не факты рантайма).

---

## 2. Быстрые проверки (ключевые числа)

| Что в паспорте | Как проверить (Windows / универсально) |
|----------------|----------------------------------------|
| `include_router` в API v1 | Поиск по `src/api/v1/router.py`: строки `^api_router.include_router` (ожидание **92** на 2026-04) |
| Файлы миграций | Glob `alembic/versions/*.py` (ожидание **91** на 2026-04) |
| Admin shell сегменты SPA | Массив `ADMIN_SHELL_ROUTE_SEGMENTS` в `frontend/src/routePaths.ts` (**45** элементов) |
| Файлы `frontend/src` | Glob `frontend/src/**/*.ts` + `**/*.tsx` (ожидание **276** на 2026-04) |
| Файлы `src/**/*.py` | Glob под `src/` (ожидание **537** на 2026-04) |
| Модули `application/services` | Glob `src/application/services/*.py` (**90** файлов; **69** с шаблоном `*_service.py`) |
| Сущности `domain/entities` | Glob `src/domain/entities/*.py` (**160** файлов, включая `__init__.py`) |
| Файлы роутеров API | Glob `src/api/v1/routers/*.py` (**93**; один без `include_router` в `router.py`) |
| Тесты Python | Glob `tests/**/*.py` (**165** на 2026-04) |

После изменения контрактов (новый роутер, миграция, экран) — обновить соответствующий паспорт и при необходимости строки в этой таблице.

---

## 3. Сопутствующие артефакты

- Автоген поверхности API: `python scripts/generate_router_surface_docs.py` → `docs/product_state/generated/router_surface/INDEX.md`.  
- RBAC-инвентарь: `python scripts/audit_rbac_endpoints.py --write` → `docs/product_state/baselines/rbac_router_permissions.txt`.

---

## 4. Карта «какой паспорт за что отвечает**

| Документ | Сверка |
|----------|--------|
| `BACKEND_PASSPORT.md` | `main.py`, `router.py`, `dependencies.py`, `config.py`, Celery, миграции |
| `FRONTEND_PASSPORT.md` | `App.tsx`, `routePaths.ts`, `main.tsx`, `client.ts`, `vite.config.ts`, `adminEntitlementNav.ts` |
| `ARCHITECTURE_FROM_CODE.md` | Точки интеграции Redis, outbox, auth, БД — grep по указанным в документе путям `src/` |
| `PROJECT_STRUCTURE_FROM_CODE.md` | Glob по деревьям; исправлять числа пачкой при расхождении |
| `FILE_MAP_MARKDOWN.md` | Не полный инвентарь всего репозитория — см. шапку файла; слой S в §4 обязан совпадать с фактическими файлами в `docs/product_state/` |

---

**Reference:** [`INDEX.md`](./INDEX.md) · [`RAG_NAVIGATION_S_LAYER.md`](./RAG_NAVIGATION_S_LAYER.md)
