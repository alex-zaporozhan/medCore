# QA_ARCH: RAG §24.3 — ревью реализации и бэклог этапов

**Дата:** 2026-04-13  
**Объект:** per-organization KB (`organization_rag_kb_documents`), admin CRUD, `POST /api/v1/public/embed/v1/rag/search`.  
**Эпик:** [STREAM_PRODUCT_RAG_24_EPIC.md](../architecture/arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md).

---

## 1. Вердикт

**Готово к эксплуатации в срезе v1** при условии зелёных интеграционных тестов на чистой тестовой БД. Контракт изоляции по `organization_id` соблюдён в коде и покрыт негативными сценариями. Часть пунктов эпика осознанно перенесена на следующие фазы (см. §5).

---

## 2. Критические риски

| Риск | Было | Действие (выполнено @QA_ARCH) |
|------|------|--------------------------------|
| Пользовательский запрос с `%` / `_` раздувал выдачу ILIKE (логические wildcards при bind-параметрах) | Средний: не инъекция, но некорректная семантика поиска | Экранирование + `ESCAPE '\'` в `search_documents_for_org`, тест на литерал `50%` |
| Тест entitlement 403 на публичном RAG в **Box/basic** редакции давал ложный fail | Критично для CI при `EDITION=box` | `@pytest.mark.skipif(is_box_edition(), …)` с явной причиной |

---

## 3. Средние риски

| Риск | Статус |
|------|--------|
| Тяжёлый ILIKE по `body` без отдельного лимита → нагрузка на БД | **Частично снят:** добавлен опциональный второй Redis-счётчик `rate_embed_rag_search_ip_*` (по умолчанию 0 = только общий embed-лимит) |
| Нет аудита мутаций KB (кто/когда) | Открыт → бэклог §5 |
| Двойной `session.commit()` в хендлерах при `get_db`, завершающем commit | Наследие паттерна; не блокер, при рефакторе — единая политика |
| Документация эпика указывала путь `src/services/…` | Исправлено в эпике на `src/application/services/…` |

---

## 4. Формально vs по сути

- **По сути сделано:** изоляция org в сервисе и публичном маршруте, entitlement `ai.rag.org_kb`, негатив cross-org embed, часть admin-изоляции.
- **Раньше было ближе к формальному:** отсутствие экранирования ILIKE; отсутствие явного учёта Box в тесте 403; хвост «отдельный rate limit» без крючка в конфиге.

---

## 5. Решения уровня @LEAD (победитель)

| Вопрос | Варианты | **Победитель** | Обоснование |
|--------|----------|----------------|---------------|
| Семантика `%` в запросе пользователя | Как wildcards / как литералы | **Литералы** (через ESCAPE) | Предсказуемость для embed-виджета и юзерского текста |
| Ужесточение RAG отдельно от прочего embed | Общий только / доп. bucket | **Доп. bucket опционально** (`RATE_EMBED_RAG_SEARCH_IP_LIMIT`, 0 = выкл.) | Соответствует хвосту эпика без ломки дефолтов |
| Тест SaaS-gate на публичном RAG в Box | Менять прод-код / skip в тесте | **Skip в тесте** | В Box публичный контур по дизайну не гейтится tariff-строками — тест проверяет Enterprise/SaaS |

---

## 6. Бэклог → исполнение (2026-04-13)

| Пункт (бывший §6) | Статус | Где |
|-------------------|--------|-----|
| Векторный retrieval + ADR | **Фаза B открыта** | [ADR-014](../adr/ADR-014-rag-retrieval-vectors-and-stores.md) (pgvector vs внешний store); контракт §24.3 зафиксирован в ADR |
| Квоты / PII | **Квоты + политика** | `RAG_KB_QUOTA_MAX_DOCUMENTS_PER_ORG`, 409 `rag_kb_quota_exceeded`; [RAG_KB_PII_AND_QUOTAS.md](../architecture/RAG_KB_PII_AND_QUOTAS.md) |
| Audit trail | **Сделано** | Таблица `organization_rag_kb_audit_log`, `rag_kb_audit_service`, admin create/update/delete |
| Метрики | **Сделано** | `embed_rag_search_duration_seconds`, `embed_rag_search_outcomes_total`; алерт `EmbedRagSearchDbErrorBurst` |
| OpenAPI 403 embed | **Сделано** | Примеры для `/rag/search` и `/assistant/message` (`entitlement_required` + keys) |
| FTS / индекс | **Сделано** | `search_tsv` GENERATED + GIN, `RAG_KB_SEARCH_MODE=ilike\|fts\|hybrid` |
| Нагрузочный профиль | **Сделано** | [LOAD_SCENARIO_RAG_KB.md](../operations/LOAD_SCENARIO_RAG_KB.md), `scripts/load_tests/README.md` |

**Остаток эпика:** внедрение **векторного** слоя (embeddings + store) по ADR-014 фаза B, после пилота нагрузки.

---

## 7. Трассировка тестов (после усиления)

| Сценарий | Файл |
|----------|------|
| Cross-org embed search | `tests/api/test_rag_org_isolation.py` |
| ILIKE литерал `%` в запросе | `tests/api/test_rag_org_isolation.py` |
| Admin DELETE/GET чужого org | `tests/api/test_rag_org_isolation.py` |
| 401 без Bearer | `tests/api/test_phase1e_embed.py` |
| 403 без `ai.rag.org_kb` (SaaS, не Box) | `tests/api/test_phase1e_embed.py` |
| Экранирование строки (unit) | `tests/core/test_rag_kb_ilike_escape.py` |
| OpenAPI success + 403 примеры embed | `tests/core/test_openapi_error_schemas.py` |
| Квота KB, аудит, FTS режим | `tests/api/test_rag_kb_phase2.py` |

---

**Версия:** 1.1 (§6 закрыт в коде; векторный RAG — бэклог ADR-014).
