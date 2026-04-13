# Карта источников правды по фронту (дедупликация RAG)

> **Версия:** 2026-04-10 (инвентарь поверхностей)  
> **Назначение:** одна тема — один первичный документ; остальное — краткое резюме и ссылка.

| Тема | Первичный источник | Дубли / расширения (только ссылка) |
|------|-------------------|-------------------------------------|
| Маршруты и стек SPA (факты) | [`../product_state/FRONTEND_PASSPORT.md`](../product_state/FRONTEND_PASSPORT.md) | `frontend/src/App.tsx`, `frontend/src/routePaths.ts` |
| Зоны, layout, Query, drawer, edition | [`FRONTEND_ARCHITECTURE_CANON.md`](./FRONTEND_ARCHITECTURE_CANON.md) | [`FRONTEND_ENGINEERING_CONVENTIONS.md`](./FRONTEND_ENGINEERING_CONVENTIONS.md), [`../architecture/frontend/routing_and_shells.md`](../architecture/frontend/routing_and_shells.md) |
| Макро/микро UI, матрица UI↔API, итерации A/B/C | [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) | — |
| Поведение экранов (шторки, табы, сущности) | [`../TECH_PASSPORT_FRONTEND_UI_LOGIC.md`](../TECH_PASSPORT_FRONTEND_UI_LOGIC.md) | [`TEMPLATE_ADMIN_UI_UX.md`](../TEMPLATE_ADMIN_UI_UX.md) |
| Тема Mantine, семантика цветов | [`UI_THEME.md`](./UI_THEME.md) | [`../ARCH_FRONTEND_UI_LOGIC.md`](../ARCH_FRONTEND_UI_LOGIC.md) |
| Роль @FRONTEND (процесс) | [`../ROLE_FRONTEND.md`](../ROLE_FRONTEND.md) | не подменяет канон и паспорт |
| Конкретный экран | файл в [`pages/`](./pages/) — с **инвентарём поверхностей** (drawer/modal/menu/stepper), см. [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md) ось H | дублировать тело в `documentation/USER_DOCS/` **нельзя** — другой контур ([`DOCUMENTATION_POLICY.md`](../../DOCUMENTATION_POLICY.md)) |

Обновление: при смене `App.tsx` / сегментов — править **сначала** `FRONTEND_PASSPORT.md`, затем индекс [`pages/README.md`](./pages/README.md).
