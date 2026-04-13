# Сценарий нагрузки: RAG KB + публичный embed `/rag/search` (§24.3)

> **Статус:** шаблон для @OPS / @QA_ARCH перед выкатом FTS/hybrid или ростом трафика виджета.  
> **Связь:** [RAG_KB_PII_AND_QUOTAS.md](../architecture/RAG_KB_PII_AND_QUOTAS.md), [ADR-014](../adr/ADR-014-rag-retrieval-vectors-and-stores.md).

## Зачем

`POST /api/v1/public/embed/v1/rag/search` при режимах `fts` / `hybrid` нагружает PostgreSQL (GIN + `@@`). Нужен базовый прогон до заявления устойчивости под X RPS.

## Предпосылки

1. Миграция `20260425_rag_kb_audit_fts` применена (`search_tsv` + GIN).
2. Redis доступен для rate limiter (если включены `RATE_EMBED_*`).
3. Тестовые embed-ключи `dceb.*` для K организаций.

## Профиль данных (ориентир)

| Параметр | Smoke | Стресс (черновик) |
|----------|-------|-------------------|
| Организаций с KB | 10 | 500+ |
| Документов на org | 50–200 | 500–2000 |
| Средний размер `body` | 1–4 KB | 4–20 KB |

## Сценарий запросов

1. **Смешанный поток:** 70% поисковых запросов (случайные токены из словаря + реальные фразы), 30% других embed-вызовов (`/session`, при необходимости assistant), чтобы лимитер и пул соединений были репрезентативны.
2. **Длина query:** 2–80 символов (границы валидации API).
3. **Режимы:** отдельные прогоны для `RAG_KB_SEARCH_MODE=ilike`, затем `hybrid` или `fts`.

## Наблюдение

- Prometheus: `embed_rag_search_duration_seconds` (p95/p99 по `search_mode`), `embed_rag_search_outcomes_total` (`empty` / `hits` / `db_error`), `embed_public_request_total{endpoint="rag_search"}`.
- Postgres: `pg_stat_statements` (если включён) — время на запросах к `organization_rag_kb_documents`.
- Алерт: `EmbedRagSearchDbErrorBurst` в `deploy/prometheus/dental_booking_alerts.yml`.

## Критерий успеха (заполнить перед прогоном)

- p95 `embed_rag_search_duration_seconds` < ___ ms при заявленном RPS.
- Доля `db_error` < ___ % в окне 15 минут.
- CPU Postgres / connection pool без устойчивого saturation.

## Артефакт

Дата, версия образа, RPS, N/K, фактический режим `RAG_KB_SEARCH_MODE`, ссылка на скрипт (например k6) при появлении в `scripts/load_tests/`.
