# Продуктовый эпик RAG §24.3 (per-organization KB)

> **МП:** §24.3 — индекс знаний строго в границах арендатора.  
> **Поток:** см. [STREAM_1E_AND_PHASE3_PLUS_EPICS.md](./STREAM_1E_AND_PHASE3_PLUS_EPICS.md) (**1e-F1**).  
> **Трассировка:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) (**RAG-24**).  
> **Приёмка @QA_ARCH:** [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**1e-F***).  
> **RAG §24.3 (риски, бэклог):** [ADR-014](../../adr/ADR-014-rag-retrieval-vectors-and-stores.md), `tests/api/test_rag_org_isolation.py`, `tests/api/test_rag_kb_phase2.py`.

---

## 1. Цель

Дать арендату управляемый **организационный KB** для сценариев embed/assistant: загрузка фрагментов текста, поиск по запросу, вызов из публичного контура **только** с валидным embed-токеном, привязанным к организации ключа.

---

## 2. Контракт изоляции (не менять при смене движка поиска)

1. **Первичный ключ разграничения:** `organization_id` на каждой строке KB и во **всех** запросах чтения/поиска (admin и public).  
2. **Публичный поиск** (`POST /api/v1/public/embed/v1/rag/search`) обязан фильтровать результаты **только** по `organization_id`, выведенному из контекста embed-сессии / ключа (не из тела запроса клиента как источника истины для границы).  
3. Смена реализации поиска (ILIKE → embeddings → vector store) — **замена слоя retrieval** при сохранении п.1–2 и негативных тестов.

**v1 (текущий срез):** таблица `organization_rag_kb_documents` + опционально **FTS** (`search_tsv` GIN, `RAG_KB_SEARCH_MODE`), аудит мутаций, квоты; **vector store** — см. [ADR-014](../../adr/ADR-014-rag-retrieval-vectors-and-stores.md) фаза B.

---

## 3. Реализация в коде (ориентиры)

| Область | Путь |
|--------|------|
| Сущность KB | `src/domain/entities/organization_rag_kb_document.py` |
| Сервис поиска | `src/application/services/organization_rag_kb_service.py` |
| Admin CRUD | `src/api/v1/routers/admin_rag_kb.py` (entitlement `ai.rag.org_kb`) |
| Публичный поиск | `src/api/v1/routers/public_embed.py` — `POST .../rag/search` |
| Аудит мутаций KB | `src/domain/entities/organization_rag_kb_audit_log.py`, `src/application/services/rag_kb_audit_service.py` |
| Миграция FTS + аудит | `alembic/versions/20260425_rag_kb_audit_fts.py` |

---

## 4. Тесты

- **Негатив cross-org:** `tests/api/test_rag_org_isolation.py` — документ org B не возвращается при поиске с ключом org A; admin GET/DELETE чужого `document_id` → 404; литерал `%` в запросе ILIKE.  
- Базовые сценарии embed: `tests/api/test_phase1e_embed.py` (401; 403 без `ai.rag.org_kb` в SaaS, не Box).  
- Unit экранирования ILIKE: `tests/core/test_rag_kb_ilike_escape.py`.  
- Квоты, аудит, FTS, OpenAPI 403: `tests/api/test_rag_kb_phase2.py`, `tests/core/test_openapi_error_schemas.py`.

---

## 5. Хвост эпика

- **Векторный retrieval** (embeddings + store): [ADR-014](../../adr/ADR-014-rag-retrieval-vectors-and-stores.md) фаза B — пилот pgvector vs внешний индекс.  
- **PII / квоты:** политика и env — [RAG_KB_PII_AND_QUOTAS.md](../RAG_KB_PII_AND_QUOTAS.md).

**Доп. лимит POST `/rag/search`:** `RATE_EMBED_RAG_SEARCH_IP_*` — см. `public_embed` и метрики `embed_rag_search_*` в коде; детали — [ADR-014](../../adr/ADR-014-rag-retrieval-vectors-and-stores.md).

## 6. Статус среза

Исполнение §6: таблица **RAG-24** / **1e-F1** в [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) и строки **1e-F*** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).

---

**Версия:** 2026-04-13 (FTS/аудит/квоты/метрики/OpenAPI/нагрузочный профиль; вектор — ADR-014).
