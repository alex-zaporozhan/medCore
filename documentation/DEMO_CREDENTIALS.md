# Demo credentials

**Local seeds and presentations only.** Do not reuse these passwords on a real deployment. Rotate every secret in `.env` before any network-exposed host.

Canonical long tables (Russian runbook, same values): [`CREDENTIALS_REFERENCE.md`](./CREDENTIALS_REFERENCE.md), [`DEMO_MULTI_TENANT_CREDENTIALS.md`](./DEMO_MULTI_TENANT_CREDENTIALS.md).

## Staff admin — `/admin/login`

### Multi-tenant showcase (5 clinics)

```bash
poetry run python -m src.scripts.seed_rbac_baseline
poetry run python -m src.scripts.seed_multi_tenant_showcase
```

Compose (no host Poetry): `bash scripts/seed_demo_compose.sh` or `scripts/seed_demo_compose.ps1` after `docker compose up -d --build --wait`.

| Field | Value |
|---|---|
| Password (all seeded staff below) | `ShowcaseMT2026!` |
| Owner example | `owner.kazan@showcase-mt.demo` |
| Doctor-role example | `doctor1.kazan@showcase-mt.demo` |
| Other cities | `nizhny`, `samara`, `krasnodar`, `rostov` — same `owner.*` / `admin*` / `marketing*` / `doctor1.*@showcase-mt.demo` pattern |

List from code: `poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials`.

Staff and patient **display names** are US-primary (Austin / Boston / Chicago) plus Lyon and Milan; chair doctors Paul / Mary / Ben; doctor-role login Hannah Cole. Five staff huddles (10 messages each), a **two-week ops huddle**, omni threads, and catalog overlay are English after `seed_multi_tenant_showcase` / `backfill_showcase_saas_extras`. Re-running the showcase seed on a marked DB applies extras **idempotently**, refreshes the English video layer (rewrites existing chat/omni copy in place), then the **±14-day ops window** (denser chair grid, Kanban due dates, staff meetings, doctor-role login `doctor1.<city>@showcase-mt.demo`). Task/meeting titles do **not** use a `Demo …` prefix. Historical Alembic catalog rows stay as-is; the seed overlays English `display_name`s. **Do not put demo rows in Alembic** (schema-only; see `docs/SEED_PROTOCOL.md`).

This seed does **not** create a platform founder.

### Presentation clinic ("DentaPro")

```bash
poetry run python -m src.scripts.seed_presentation_showcase
```

| Role | Email | Password |
|---|---|---|
| Owner-class admin | `admin@dentapro.demo` | `Presentation2026!` |
| Manager | `manager@dentapro.demo` | `Presentation2026!` |

Do not mix this seed with the multi-tenant showcase on one database unless you know you want both.

### Minimal seed

`poetry run python -m src.scripts.seed_demo_data` → `admin@example.com` / `admin12345` (only if that clinic has no admin yet).

## Platform founder — `/platform/login`

No password is committed. Create one:

```bash
poetry run python -m src.scripts.create_platform_founder_user --email you@example.com --password '<your password>'
```

Production-like setups also need `PLATFORM_FOUNDER_JWT_SECRET` (separate from `JWT_SECRET_KEY`). Empty secret → platform internal routes 503.

## Compose infrastructure (not product users)

| Thing | Default in `.env.example` |
|---|---|
| PostgreSQL | `postgres` / `postgres` |
| Database names | `dental_booking`, `dental_booking_test` |

## If sign-in fails

1. Seeds were not run after `alembic upgrade head`.
2. You are on the wrong page (patient OTP vs `/admin/login` vs `/platform/login`).
3. Frontend cannot reach the API (Vite on **5175** proxies `/api` to host **8000** or Compose **8010**; Compose UI on **3010** proxies `/api` to the backend service).

Smoke without a browser (host-run API):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"owner.kazan@showcase-mt.demo\",\"password\":\"ShowcaseMT2026!\"}"
```

Compose-published API: same path on `http://127.0.0.1:8010`. Expect JSON with `access_token`.
