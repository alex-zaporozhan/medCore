# Слой S: индекс паспортов по коду

> **Версия:** 2026-04-10  
> **Приоритет истины:** репозиторий (код и тесты) → этот каталог → остальной `docs/` (процесс и роли).

Ниже **шесть** паспортов по задаче @LEAD, плюс **навигация слоя S** для RAG; рядом — карта markdown, аудит @QA_ARCH и файл доработок. Поверхность API v1 (автоген): `generated/router_surface/INDEX.md` (см. `scripts/generate_router_surface_docs.py`).

| # | Документ | Содержание |
|---|----------|------------|
| S0 | [RAG_NAVIGATION_S_LAYER.md](./RAG_NAVIGATION_S_LAYER.md) | Порядок чтения слоя S: mermaid-граф, вопрос→документ, связь с `RAG_CANON` / `DOC_TOPOLOGY` |
| 1 | [BACKEND_PASSPORT.md](./BACKEND_PASSPORT.md) | Стек, `main.py`, счётчик `include_router`, auth/RBAC/edition, Redis/outbox/backup/replica, config, сервисы, Celery, миграции, тесты, compose |
| 2 | [FRONTEND_PASSPORT.md](./FRONTEND_PASSPORT.md) | Стек, зоны SPA, **45** admin-сегментов, auth (admin/patient/founder), React Query + PWA SW, entitlements UI, прокси Vite, Docker; детализация экранов — [../frontend/pages/README.md](../frontend/pages/README.md); конвенции — [../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md) |
| 3 | [ARCHITECTURE_FROM_CODE.md](./ARCHITECTURE_FROM_CODE.md) | Слои backend, cross-cutting, event bus, мультитенантность; **§10–16** — JWT/auth, Redis, БД/replica, логический backup, domain outbox, scaling (честные ограничения), ER-обзор |
| 4 | [PROJECT_STRUCTURE_FROM_CODE.md](./PROJECT_STRUCTURE_FROM_CODE.md) | Дерево каталогов `src/`, `frontend/`, `tests/`, `deploy/`, связь с compose |
| 5 | [COMMERCIAL_VALUE_FROM_CODE.md](./COMMERCIAL_VALUE_FROM_CODE.md) | Ценность **только** из реализованных модулей; Box vs Enterprise; one-pager: [COMMERCIAL_VALUE_ONE_PAGER_RU.md](./COMMERCIAL_VALUE_ONE_PAGER_RU.md) |
| 6 | [FILE_MAP_MARKDOWN.md](./FILE_MAP_MARKDOWN.md) | Срез якорных `.md` (корень репо, корень `docs/`, слой S); **не** исчерпывающий список всех markdown |
| **Клиенту** | [CLIENT_STRUCTURE_AND_VALUE.md](./CLIENT_STRUCTURE_AND_VALUE.md) | Один файл: структура репо + бизнес-ценность (без внутреннего жаргона RAG) |
| **SV** | [PRODUCT_STATE_VERIFICATION.md](./PRODUCT_STATE_VERIFICATION.md) | @QA_ARCH: как сверять числа в паспортах с кодом (glob, приоритет истины) |

**Отдельно (не смешивать с фактами):** [RAG_NECESSARY_IMPROVEMENTS.md](./RAG_NECESSARY_IMPROVEMENTS.md) — пробелы, риски, долг документации и кода.

**Аудит RAG (@QA_ARCH):** [QA_ARCH_RAG_AUDIT.md](./QA_ARCH_RAG_AUDIT.md)

**Вход в каталог:** [README.md](./README.md)

---

*Ранее единый свод `RAG_STATUS_FROM_CODE.md` заменён этим индексом и шестью паспортами — так проще навигировать и индексировать RAG.*
