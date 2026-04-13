# Необходимая доработка: пробелы, риски, рассинхрон с кодом

> **Версия:** 2026-04-03 (обновление после @QA_ARCH)  
> **Область:** оценка зрелости и долга; **не** дублирует факты из паспортов в [INDEX.md](./INDEX.md).

---

## Выполнено в проходе @QA_ARCH (зафиксировать, не откатывать)

| Было | Сделано |
|------|---------|
| `RAG_CANON` / `DOC_TOPOLOGY` | Выравнивание под **код → `product_state` (S) → P**; слой **W = `docs/artifacts/`** сохранён по `.cursorrules`. |
| `DOCUMENTATION_POLICY` / `README` про `documentation/` | Выровнены под **`docs/`** + **`docs/product_state/`**. |
| Мёртвые `documentation/*.md` в `src/` и `frontend/src/` | Убраны; введено правило **без ссылок на `*.md` в прикладном коде** (см. [QA_ARCH_RAG_AUDIT.md](./QA_ARCH_RAG_AUDIT.md)). |
| CI link-check только на `documentation/` | Workflow переведён на **`docs/`**, `README.md`, `DOCUMENTATION_POLICY.md`. |
| Grafana/Prometheus ссылки на несуществующий OBSERVABILITY | Заменены на **`docs/METRICS_PROTOCOL.md`** и **`deploy/grafana/README.md`**. |
| Инвентарь RBAC в несуществующем пути | **`docs/product_state/baselines/rbac_router_permissions.txt`** + скрипт `audit_rbac_endpoints.py`. |
| Нет автоген поверхности API | **`docs/product_state/generated/router_surface/INDEX.md`** + `generate_router_surface_docs.py`. |
| Выравнивание ROLE ↔ `.cursorrules` | **`docs/ROLE_*.md`** снова согласованы со **слой W = `docs/artifacts/`**; **`docs/product_state/`** — слой S (паспорта по коду), без подмены W. |

---

## 1. Остающийся долг (актуально)

### 1.1. Старые markdown в `docs/` (слой P)

**`docs/ROLE_*.md`** должны совпадать с **`.cursorrules`**: слой W — **`docs/artifacts/`**. Остальной **`docs/*.md`** (`TPF_*`, шаблоны) — чистить устаревшие ссылки на `documentation/` **по мере обнаружения**.

### 1.2. Правило «без .md в коде» — закрепить инструментом

Рекомендуется pre-commit или CI-шаг: запрет `\documentation/` и regex на `\.md` внутри `src/` и `frontend/src/` (с allowlist только если неизбежно).

### 1.3. Backend: `GET /health/replica`

В `src/main.py` при ошибке пробы реплики в ответе может быть `error: str(exc)` — утечка деталей наружу. Смягчить для production.

### 1.4. Celery stub

При отсутствии пакета `celery` импорт не падает — помнить для сред, где worker обязателен.

### 1.5. Согласованность Box / Enterprise

Один контракт `.env` / compose для `EDITION` и `VITE_EDITION`; дымовой тест.

---

## 2. Приоритизация (остаток)

| Приоритет | Действие |
|-----------|----------|
| P1 | Grep по **`docs/*.md`** (кроме **`ROLE_*.md`**, где пути к W зафиксированы) на устаревший `documentation/` — править по `DOCUMENTATION_POLICY.md`. |
| P1 | Автоматическая проверка отсутствия `.md` ссылок в `src/`, `frontend/src/`. |
| P2 | OpenAPI snapshot в CI. |
| P2 | `/health/replica` без `str(exc)` в теле ответа клиенту. |

---

**Reference:** [QA_ARCH_RAG_AUDIT.md](./QA_ARCH_RAG_AUDIT.md) · `docs/RAG_CANON.md`
