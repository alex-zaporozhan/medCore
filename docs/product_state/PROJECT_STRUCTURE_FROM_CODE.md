# Структура проекта (дерево и назначение каталогов)

> **Версия:** 2026-04-10 (@QA_ARCH: сверка glob с репозиторием)  
> **Метод:** фактическое дерево репозитория; цифры — счётчики по glob на дату среза (пересчитывать при крупных PR). Регламент сверки: [`PRODUCT_STATE_VERIFICATION.md`](./PRODUCT_STATE_VERIFICATION.md).

---

## 1. Корень репозитория

| Путь | Назначение |
|------|------------|
| `src/` | Исходный код backend Python |
| `frontend/` | SPA: React/Vite, Dockerfile, `package.json`, статика PWA |
| `tests/` | Pytest: API, сервисы, security, e2e |
| `alembic/` | `env.py`, `script.py.mako`, `versions/*.py` — миграции |
| `deploy/` | Grafana JSON, Prometheus alerts |
| `scripts/` | Shell/PowerShell/Python вспомогательные скрипты (dev, security, ops) |
| `docs/` | Markdown: канон RAG, роли, шаблоны, `architecture/`, `adr/`, `artifacts/` (слой W), `frontend/`, `operations/`, `design/`, `review/` |
| `docs/product_state/` | Слой S: паспорта и статус **по коду** |
| `documentation/` | Публично ориентированные материалы (см. `DOCUMENTATION_POLICY.md`) |
| `docker-compose.yml` | Локальный полный стек + profile e2e |
| `Dockerfile` | Сборка backend-образа |
| `pyproject.toml` / `poetry.lock` | Зависимости и инструменты Python |
| `.github/` | Шаблоны PR, workflows |
| `.env.example` | Шаблон переменных окружения (если присутствует в репо) |
| `Jenkinsfile` | CI/CD pipeline (релизные образы; см. `CI_CD.md`) |
| `CI_CD.md` / `AGENTS.md` | Канон: Jenkins + GHCR |

---

## 2. Backend: `src/`

```
src/
├── main.py                 # FastAPI app, middleware, health, metrics
├── api/v1/
│   ├── router.py           # Сборка всех роутеров
│   ├── dependencies.py     # Auth, RequestContext, require_permissions
│   └── routers/            # 93 .py (включая `_admin_staff_common`; в `router.py` — 92× `include_router`)
├── application/
│   ├── services/           # 90 .py (прикладная логика и вспомогательные модули)
│   ├── dto/
│   ├── events/
│   ├── rbac_matrix.py
│   └── …
├── domain/
│   ├── entities/           # 160 .py (включая `__init__.py`)
│   └── interfaces/repositories/
├── infrastructure/
│   ├── database/           # Репозитории, base session
│   ├── messaging/        # celery_app, tasks/*
│   ├── storage/
│   ├── realtime/
│   ├── external_apis/
│   └── rate_limiter.py
├── core/                   # config, logging, metrics, security, edition, …
└── scripts/                # seed и прочие утилиты
```

**Объём:** **537** файлов `.py` под `src/` (glob на 2026-04).

---

## 3. Frontend: `frontend/`

```
frontend/
├── index.html              # entry → /src/main.tsx
├── vite.config.ts
├── package.json
├── Dockerfile
├── public/                 # PWA иконки, ассеты
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── routePaths.ts
    ├── theme.ts
    ├── api/
    ├── admin/              # pages (≈49 tsx в pages), layouts, components
    ├── app/pages/          # пациентские экраны
    ├── marketing/
    ├── hooks/
    ├── contexts/
    ├── shared/
    ├── config/edition.ts
    ├── pwa/
    └── __tests__/
```

**Объём:** **276** `.ts`/`.tsx` под `frontend/src/` (glob на 2026-04).

---

## 4. Тесты: `tests/`

```
tests/
├── conftest.py
├── api/                    # интеграционные HTTP-тесты
├── services/
├── security/
├── e2e/                    # Playwright
├── core/
├── application/
└── unit/
```

**Объём:** **165** файлов `.py` под `tests/` (glob на 2026-04).

---

## 5. Миграции: `alembic/versions/`

- **91** файл ревизий `.py` (включая merge-heads; glob `alembic/versions/*.py` на 2026-04).

---

## 6. Наблюдаемость: `deploy/`

- `deploy/grafana/dashboards/*.json`
- `deploy/prometheus/*.yml`

---

## 7. Документация

- **`docs/`** — инженерия: корневые md, подкаталоги `architecture/`, `adr/`, `artifacts/` (процесс, слой W), `frontend/`, `operations/`, `design/`, `review/` и др. Полный перечень `.md` не дублируется здесь — см. [`FILE_MAP_MARKDOWN.md`](./FILE_MAP_MARKDOWN.md) и ограничения среза там же.
- **`documentation/`** — пользовательский контур (см. `DOCUMENTATION_POLICY.md`).
- **`docs/product_state/`** — слой S (этот каталог).

---

## 8. Связь структуры с runtime (compose)

| Сервис compose | Код / артефакт |
|----------------|----------------|
| `migrations` | `alembic upgrade head` в образе backend |
| `backend` | `uvicorn src.main:app` |
| `celery` | `celery -A src.infrastructure.messaging.celery_app worker` |
| `celery-beat` | `celery … beat` |
| `frontend` | Статика из `frontend/Dockerfile` |
| `db` | Postgres 16 |
| `redis` | Redis 7 |

---

**Reference:** listing `src/`, `frontend/src/`, `tests/`, `alembic/versions/`, `docker-compose.yml`.
