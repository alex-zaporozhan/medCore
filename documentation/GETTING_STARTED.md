# Getting started

English runbook for a local demo. Deeper pytest / connection-budget notes: [`DEVELOPMENT.md`](./DEVELOPMENT.md) (that file is still partly Russian).

## Prerequisites

- Docker with Compose v2.20+ (`--wait` on `up`)
- Optional host path: Python 3.11, [Poetry](https://python-poetry.org/), Node 18+

## Compose (UI + API + workers)

```bash
cp .env.example .env
# set SECRET_KEY and JWT_SECRET_KEY to long random values
docker compose up -d --build --wait
```

| Service | Host |
|---|---|
| Frontend | http://127.0.0.1:3010  (`/api` proxied to backend) |
| API | http://127.0.0.1:8010 (`/health`, `/docs`) |
| Postgres | `localhost:5442` |
| Redis | `localhost:6380` |

Compose service names are **`db`** and **`redis`**. `docker compose up -d postgres` will fail with `no such service`.

`Container … Waiting` during startup is the healthcheck on `db` / `redis`. That is not a hang until it stays there past a minute — then: `docker compose logs db`.

The `migrations` container is a one-shot. **Exit 0** is success.

### Seed demo users

Do this **in the backend container** so a clone-only Docker user can log in (no host Poetry):

```bash
bash scripts/seed_demo_compose.sh
# Windows:
# powershell -ExecutionPolicy Bypass -File scripts/seed_demo_compose.ps1
```

Host Poetry, if you already have it, with `DATABASE_URL` aimed at `localhost:5442`:

```bash
poetry install
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

Heavier single-clinic demo: `poetry run python -m src.scripts.seed_presentation_showcase` (do not mix with the multi-tenant showcase unless you intend to).

Logins: [`DEMO_CREDENTIALS.md`](./DEMO_CREDENTIALS.md). Staff sign-in is **`/admin/login`**, not the patient phone flow and not `/platform/login`.

## Host-run API (hot reload)

Postgres image already creates `POSTGRES_DB` (`dental_booking`) on first volume init. Create the **test** database once:

```bash
docker compose up -d db redis
docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"
cp .env.example .env
poetry install
poetry run alembic upgrade head
poetry run uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

If `dental_booking_test` already exists, ignore the CREATE error.

```bash
cd frontend
npm install
npm run dev
```

Vite (typically port **5175**) proxies `/api` to a live API: host uvicorn on **8000**, or Compose on **8010** if 8000 is down. The proxy target is re-probed every 4s in `dev`/`preview` (not during `vite build`). Override with `VITE_API_PROXY_TARGET`. `npm run preview` (port **4173**) uses the same proxy. Do not add `frontend/vite.config.js` — on Windows Vite would prefer it over `vite.config.ts`.

PowerShell: a session-level `DATABASE_URL` overrides `.env`. If passwords look "wrong": `Remove-Item Env:DATABASE_URL`.

## Tests

```bash
# .env: DATABASE_URL_TEST=.../dental_booking_test
poetry run python scripts/upgrade_test_db.py
poetry run pytest tests/ -q
cd frontend && npm test
```

`alembic upgrade head` follows `DATABASE_URL`, not `DATABASE_URL_TEST`. Use `scripts/upgrade_test_db.py` for the test database.

Do not run the full pytest suite against the same Postgres instance as a live `backend` + `celery` compose stack. Connection budget is shared (`max_connections`).

## Observability (optional)

```bash
docker compose --profile observability up -d
```

Prometheus: `http://127.0.0.1:9090` (loopback). Grafana: `http://127.0.0.1:3001` (default login `admin` / `GRAFANA_ADMIN_PASSWORD`, often `admin`).

## VPS images

Local build + Docker Hub: [`VPS_IMAGE_AND_DATA.md`](./VPS_IMAGE_AND_DATA.md), scripts `scripts/docker_hub_release.ps1` / `.sh`. Jenkins → GHCR: [`CI_CD.md`](../CI_CD.md).
