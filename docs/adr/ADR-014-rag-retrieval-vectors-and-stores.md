# ADR-014: Эволюция RAG retrieval (§24.3) — FTS, векторы, внешние сторы

**Статус:** Proposed (часть **Accepted** в коде: PostgreSQL FTS + конфиг `rag_kb_search_mode`, см. миграцию `20260425_rag_kb_audit_fts`).  
**Дата:** 2026-04-13  
**Контекст:** [STREAM_PRODUCT_RAG_24_EPIC.md](../architecture/arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md), `tests/api/test_rag_org_isolation.py`, `tests/api/test_rag_kb_phase2.py`.

## Контекст

Per-organization KB v1 использовал ILIKE по `title`/`body`. При росте объёма и запросов на «смысловой» поиск нужны:

1. Полнотекстовый поиск с индексом (дешевле полного скана по `body`).
2. Семантический поиск (embeddings + ближайшие соседи).
3. Сохранение **контракта изоляции §24.3**: `organization_id` для фильтрации всегда из контекста ключа embed / эффективной org админа, не из недоверенного поля клиента.

## Решение (поэтапно)

### Фаза A — принято в коде (2026-04-13)

- Колонка `search_tsv` **GENERATED STORED** (`to_tsvector('simple', title || body)`), индекс **GIN**.
- Режимы `RAG_KB_SEARCH_MODE`: `ilike` (по умолчанию), `fts`, `hybrid` (FTS, при пустой выдаче — ILIKE).
- Конфигурация через Settings; переключение без смены кода приложения.

### Фаза B — векторный retrieval (кандидаты)

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **B1. pgvector** в той же Postgres | Одна БД, транзакции, RLS-совместимость в перспективе | Размер БД, нагрузка на primary, миграции индекса |
| **B2. Управляемый vector store** (OpenSearch, Pinecone, …) | Масштаб чтения, специализированные индексы | Ещё один контур, синхронизация, стоимость, data residency |
| **B3. Внешний LLM+RAG SaaS** | Быстрый time-to-market | Слабый контроль изоляции, вендор-лок |

**Победитель по умолчанию для enterprise-контроля:** **B1 (pgvector)** при условии пилота на staging: p95 latency поиска, стоимость хранения, бэкапы. **B2** — если нагрузка чтения или политика residency требуют отдельного кластера.

### Фаза C — политика и границы

- Любой движок поиска остаётся **за** слоем `search_documents_for_org` (или преемником) с обязательным предикатом `organization_id = :resolved_org`.
- Негативные тесты cross-org обязательны при смене движка.
- Embedding-модель и размер чанка — отдельное решение @LEAD + @SEC (PII в тексте).

## Последствия

- Операции: при `rag_kb_search_mode=fts|hybrid` нужна применённая миграция `20260425_rag_kb_audit_fts`.
- Наблюдаемость: метрики `embed_rag_search_*` (см. `src/core/metrics.py`).

## Ссылки

- Код: `src/application/services/organization_rag_kb_service.py`, `src/api/v1/routers/public_embed.py`
- Политика PII/квоты: [RAG_KB_PII_AND_QUOTAS.md](../architecture/RAG_KB_PII_AND_QUOTAS.md)
