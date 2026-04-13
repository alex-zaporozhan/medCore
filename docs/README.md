# Документация репозитория

> **Версия:** 2026-04-03 (аудит @QA_ARCH)

## Для AI и RAG

1. **`docs/RAG_CANON.md`** — порядок источников и правила при дублях.  
2. **`docs/product_state/INDEX.md`** — паспорта **по коду** (backend, frontend, архитектура, структура, ценность, карта всех `.md`).  
3. Остальной каталог **`docs/*.md`** — процесс, роли, шаблоны (слой P); не подменяет код как описание «что уже работает».

**Слой W (`docs/artifacts/`)** и каталог **`documentation/`** в git **не используются** (намеренно). Исторические ссылки в старых ролевых файлах считать устаревшими; истина о продукте — **код** + **`product_state/`**.

## Для людей

| Документ | Зачем |
|----------|--------|
| [RAG_CANON.md](./RAG_CANON.md) | Канон для ответов о продукте и коде |
| [DOC_TOPOLOGY.md](./DOC_TOPOLOGY.md) | Слои S/P и правила размещения |
| [product_state/INDEX.md](./product_state/INDEX.md) | Оглавление паспортов из кода |
| [product_state/FILE_MAP_MARKDOWN.md](./product_state/FILE_MAP_MARKDOWN.md) | Полный список `.md` в репозитории |
| [ENGINEERING_PLAN.md](./ENGINEERING_PLAN.md) | Роли, ворота, Transmission Protocol |
| [RUN_SERVICES.md](./RUN_SERVICES.md) | Запуск и перезапуск сервисов |
| [MIGRATION_UPGRADE.md](./MIGRATION_UPGRADE.md) | Миграции БД |

[DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) — если используется как указатель, пусть ведёт на **код** и **`product_state/INDEX.md`**, а не на несуществующие пути.

---

Reference: корневой `README.md` (запуск), [`product_state/COMMERCIAL_VALUE_FROM_CODE.md`](./product_state/COMMERCIAL_VALUE_FROM_CODE.md) (интерпретация модулей из кода)
