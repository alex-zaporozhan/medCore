# product_state (слой S) — снимки «что есть в коде»

> **Версия:** 2026-04-10  
> **Назначение:** allowlist для RAG: документы, выведенные **только** из анализа репозитория. Не подменяют собой код и не восстанавливают удалённые волны артефактов.

## С чего начать

**[INDEX.md](./INDEX.md)** — оглавление: шесть паспортов + навигация S + файл доработок. **Порядок чтения для RAG:** [RAG_NAVIGATION_S_LAYER.md](./RAG_NAVIGATION_S_LAYER.md).

## Файлы каталога

| Файл | Роль |
|------|------|
| [INDEX.md](./INDEX.md) | Оглавление слоя S |
| [RAG_NAVIGATION_S_LAYER.md](./RAG_NAVIGATION_S_LAYER.md) | Навигация слоя S (граф, маршрутизация вопросов) |
| [BACKEND_PASSPORT.md](./BACKEND_PASSPORT.md) | Паспорт backend |
| [FRONTEND_PASSPORT.md](./FRONTEND_PASSPORT.md) | Паспорт frontend |
| [ARCHITECTURE_FROM_CODE.md](./ARCHITECTURE_FROM_CODE.md) | Архитектура по коду |
| [PROJECT_STRUCTURE_FROM_CODE.md](./PROJECT_STRUCTURE_FROM_CODE.md) | Структура репозитория |
| [COMMERCIAL_VALUE_FROM_CODE.md](./COMMERCIAL_VALUE_FROM_CODE.md) | Коммерческая ценность из фич в коде |
| [FILE_MAP_MARKDOWN.md](./FILE_MAP_MARKDOWN.md) | Срез якорных `.md` (не полный инвентарь репозитория) |
| [PRODUCT_STATE_VERIFICATION.md](./PRODUCT_STATE_VERIFICATION.md) | Сверка паспортов с кодом (@QA_ARCH) |
| [CLIENT_STRUCTURE_AND_VALUE.md](./CLIENT_STRUCTURE_AND_VALUE.md) | Клиентский одностраничник (структура + ценность) |
| [RAG_NECESSARY_IMPROVEMENTS.md](./RAG_NECESSARY_IMPROVEMENTS.md) | Только пробелы/риски/как чинить (отдельно от фактов) |
| [QA_ARCH_RAG_AUDIT.md](./QA_ARCH_RAG_AUDIT.md) | Проверка слоя S и канона; правило «без .md в прикладном коде» |

**Служебно:** `baselines/` (например инвентарь RBAC), `generated/` (автоген из `scripts/`, можно не индексировать в RAG целиком).

Остальной `docs/` — процесс и роли (слой P), рабочие материалы волны `docs/artifacts/` (слой W). Канон чтения и приоритет источников: `docs/RAG_CANON.md`.
