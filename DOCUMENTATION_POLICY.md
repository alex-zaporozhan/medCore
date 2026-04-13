# Политика документации (репозиторий)

> **Версия:** 2026-04-10 (фаза 3: навигация `architecture/`, слой W)  
> **Аудитория:** участники команды, интеграторы, индексация RAG.

## Два контура в git

| Контур | Каталог | Содержание |
|--------|---------|------------|
| **Инженерия** | **`docs/`** | Архитектура ([`docs/architecture/INDEX.md`](docs/architecture/INDEX.md)), роли, review, `docs/design/`, слой S — `docs/product_state/`, слой W — `docs/artifacts/` (процесс, не факты кода), рубрики. Порядок для AI: [`docs/RAG_CANON.md`](docs/RAG_CANON.md), карта папок: [`docs/DOC_TOPOLOGY.md`](docs/DOC_TOPOLOGY.md). |
| **Клиенты и пользователи** | **`documentation/`** | Публично ориентированные материалы: обзоры продукта, user-facing гайды (`documentation/USER_DOCS/`), питч, то, что можно отдавать интеграторам без внутренних регламентов. Технический канон по теме UI для разработчиков — в **`docs/frontend/UI_THEME.md`**. |

**Корень репозитория:** `README.md`, `CONTRIBUTING.md`, **`CI_CD.md`**, **`AGENTS.md`**, этот файл.

## Слой S (факты по коду)

- **`docs/product_state/`** — паспорта и снимки строго по коду. Вход: [`docs/product_state/INDEX.md`](docs/product_state/INDEX.md).

## CI/CD (канон репозитория)

- **Сборка образов, публикация и деплой** — **`Jenkinsfile`** и **`CI_CD.md`**. Реестр: **GHCR (`ghcr.io`)**.
- Workflow в **`.github/workflows/`** — дополнение к PR, не замена Jenkins для релизного образа.

## Чего нет в git

- Закрытые рабочие материалы команды — вне репозитория, без ссылок из прикладного кода.

## Архивы

- Каталоги `docs_archives`, `docs_archive` и аналоги в **`.gitignore`** — не коммитить.

## Код (жёстко)

- Прикладной код в **`src/`** и **`frontend/src/`** не содержит ссылок на **`*.md`** и путей `documentation/…` / `docs/….md` в пользовательских строках и docstring’ах. Канон — код и при необходимости **`docs/product_state/`**.
- Исключение: скрипты в **`scripts/`** могут писать markdown в **`docs/product_state/generated/`**.
- Внутренние роли (`@LEAD` и т.д.) не в UI.

## Авторы продуктовых текстов

- Обновление слоя S: [`docs/product_state/RAG_NECESSARY_IMPROVEMENTS.md`](docs/product_state/RAG_NECESSARY_IMPROVEMENTS.md).  
- Политика русского копирайта в UI: [`docs/COPY_STYLE_POLICY_RU.md`](docs/COPY_STYLE_POLICY_RU.md).

---

Reference: [`docs/RAG_CANON.md`](docs/RAG_CANON.md) · [`docs/DOC_TOPOLOGY.md`](docs/DOC_TOPOLOGY.md) · [`README.md`](README.md)
