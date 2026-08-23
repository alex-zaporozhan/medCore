<div align="center">

# MedCore

### A multi-tenant clinic operating system — and the first proof of [LEO](https://github.com/alex-zaporozhan/leo)

A modular monolith for clinic operations: booking, CRM, ERP, omnichannel messaging, tasks, finance, patient PWA, and a vendor-side platform contour. Shipped as one repository, not a slide deck.

The application code in this repo was **not hand-typed**. It was written by a coding agent operating under **[LEO](https://github.com/alex-zaporozhan/leo)** — a written constitution of roles, laws, and gates. I directed the process. The agent executed it. This is the debut run of that process, published with its roughness intact.

[![License: PolyForm Shield 1.0.0](https://img.shields.io/badge/license-PolyForm%20Shield%201.0.0-blue)](./LICENSE)
[![Source-available](https://img.shields.io/badge/license%20type-source--available-informational)](./documentation/LICENSING.md)
[![Stack: FastAPI · React](https://img.shields.io/badge/stack-FastAPI%20%C2%B7%20PostgreSQL%20%C2%B7%20React-black)](#stack)
[![Built with LEO](https://img.shields.io/badge/built%20with-LEO-orange)](https://github.com/alex-zaporozhan/leo)

[What this is](#what-this-is) · [How it was built](#how-it-was-built) · [Architecture](#architecture) · [Quick start](#quick-start) · [Known limitations](#known-limitations) · [License](#license)

</div>

---

## What this is

MedCore is a **shared-schema multi-tenant clinic OS** (dental vertical first). Tenancy is `Organization → Clinic`, with a separate founder/vendor contour at `/platform/*`. It is **not** a single-clinic box install.

| Contour | Who | Where |
|---|---|---|
| Public / marketing | Incoming clinics | `/`, `/signup` |
| Clinic operations | Staff (RBAC) | `/admin/*` |
| Patient | Patients | `/c/:clinicSlug/*`, `/app/*` |
| Platform | Vendor / founder | `/platform/*` |

What is actually in the tree (verified against code, not a pitch):

- **Booking and schedule** — chair/slot booking with a PostgreSQL advisory lock on the competing slot (`src/application/booking_slot_advisory_lock.py`). An `if` in application code is treated as a UX hint, not as protection.
- **RBAC** — 49 permission codes mapped to `owner` / `manager` / `admin` / `doctor`. CI diffs every router's `require_permissions(...)` against the matrix (`tests/application/test_sec_rbac_router_permissions_inventory.py`, snapshot `documentation/rbac_router_permissions.txt`).
- **CRM, tasks/Kanban, omnichannel chat, loyalty, finance, inventory, payroll** — separate admin surfaces, not one CRUD table wearing different labels.
- **Transactional outbox** — Celery + Redis for notifications and provision side-effects; workers are the same product, not a second service.
- **Observability** — `/health`, `/metrics` (Prometheus), Grafana dashboards under `deploy/`.
- **Tests** — 190+ pytest modules with `test_*` functions (this tree), **800+ collected cases** on the last full `pytest --collect-only` recorded for the LEO case study, plus Vitest and Playwright.

Full product map: [`documentation/PRODUCT_OVERVIEW.md`](./documentation/PRODUCT_OVERVIEW.md).

---

## Screenshots

Drop PNGs into [`docs/public/screenshots/`](./docs/public/screenshots/) using the filenames in that folder's README. Until then, clone and run — the software is the evidence, not a marketing site.

```
docs/public/screenshots/
  admin-schedule.png      # clinic week grid
  admin-dashboard.png     # staff home
  admin-omni-chat.png     # omnichannel inbox
  admin-tasks.png         # Kanban
  patient-booking.png     # patient PWA
```

A Playwright helper lives at `frontend/e2e/readme-screenshots.spec.ts` (`README_SCREENSHOTS=1`). It needs a running API + seeded demo. Against Compose UI set `BASE_URL=http://127.0.0.1:3010` so preview on :4173 is not also started. Patient PWA shots are still manual.

---

## How it was built

I came into software between intern and junior, in a hiring freeze that would not give production experience to anyone who did not already have it. Toy CRUD and LeetCode do not close that gap. This clinic OS was the challenge I set myself: ship something with real invariants — no double-booking, no tenant leak, no UUID in a manager-facing table — or admit I could not.

I did not have a senior team. I also did not have, as internalized skill, the knowledge that actually decides whether a system like this holds: concurrency, tenancy, RBAC drift, outbox semantics, lock lifetimes, adversarial review. That knowledge exists; it just was not in my hands yet. So I wrote it down as rules an agent would have to follow, and I sat in the seat of the person who routes, refuses, and publishes.

That rule system became **[LEO — Lead Engineering Orchestrator](https://github.com/alex-zaporozhan/leo)**. MedCore is the first end-to-end product it shipped, when LEO was thinner than the 41-law / 22-role constitution it is now. Later client work made the laws sharper. This repository is the debut, not the polished flagship — published with the scars visible, because a cleaned-up demo would prove the wrong thing.

The claim is **not** "no-code" in the Bubble/Airtable sense. This is a real FastAPI / React / PostgreSQL codebase. The claim is about **authorship and process**:

- I did not hand-write the application code.
- A coding agent (`@DEV` in LEO) wrote it.
- Every other LEO role writes artifacts and vetoes — architecture spines, QA reports, threat models — not code.
- I remain the human publish gate (LEO Law 40): the agent prepares; a person commits.

If you want the process, not the clinic domain: **[github.com/alex-zaporozhan/leo](https://github.com/alex-zaporozhan/leo)**. The longer origin note is [`documentation/ORIGIN.md`](./documentation/ORIGIN.md).

---

## Architecture

```
src/api  →  src/application  →  src/domain  →  src/infrastructure
```

One deployable. Celery workers share the same codebase. That is a **modular monolith**, not microservices.

```
Platform (founder / vendor)          /platform/*
  └── Organization (SaaS tenant)
        └── Clinic (operational tenant)
              ├── Staff  — JWT realm admin, 49-code RBAC
              └── Patient — JWT realm patient, PWA
```

Isolation today is **application-layer** (`clinic_id` / `organization_id` in services and repositories) plus cross-tenant negative tests. PostgreSQL RLS is used selectively (e.g. `organization_entitlements`), not as the sole control on every table ([ADR-007](./docs/adr/ADR-007-platform-multitenancy-super-admin.md)). Shared-schema multi-tenant is the truth. Database-per-tenant is not what this repo is.

`EDITION=box|basic` in the code is a **legacy SKU cut**, not the product architecture. Default is the full platform.

---

## Stack

| Layer | Choice |
|---|---|
| API | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| Domain / DB | SQLAlchemy 2 (async), asyncpg, Alembic, PostgreSQL 16 |
| Jobs / cache | Celery 5, Redis 7 |
| Frontend | React 18, TypeScript, Vite 6, Mantine 7, TanStack Query 5 |
| Quality | pytest, ruff / black / mypy, vitest, Playwright |
| Ship | Docker Compose; Jenkins → GHCR; GitHub Actions as PR gates; optional Docker Hub for a single VPS |

Integrations (payments, SMS, OAuth, captcha, OpenAI-compatible AI) are **config-gated**: no key, the module stays quiet. Demo seeds may use Russian payment/SMS providers; they are adapters, not the domain model.

---

## Repository map

```
.
├── src/                    # FastAPI app — api / application / domain / infrastructure
├── frontend/               # Vite SPA — marketing, /admin, patient PWA, /platform
├── tests/                  # pytest (API, services, security, outbox, tenancy)
├── alembic/                # schema migrations
├── deploy/                 # Prometheus / Grafana
├── documentation/          # public docs (start here after this README)
├── docs/adr/               # architecture decision records
├── docker-compose.yml
├── LICENSE                 # PolyForm Shield 1.0.0
└── SECURITY.md
```

Internal engineering notes under `docs/` are process history and passports. They are not the public front door. If a sentence in an older `.md` disagrees with the code, the **code wins**.

---

## Quick start

You need Docker, and — for the host-run path — Python 3.11 + Poetry and Node 18+.

### One-command stack

```bash
cp .env.example .env          # set SECRET_KEY and JWT_SECRET_KEY
docker compose up -d --build --wait
```

`--wait` needs Compose v2.20+ (waits until `backend` is healthy). Migrations are a one-shot; **exit 0** is success.

- UI: [http://127.0.0.1:3010](http://127.0.0.1:3010)
- API: [http://127.0.0.1:8010](http://127.0.0.1:8010) — `/health`, `/docs` (docs off in production)
- Compose service names are `db` and `redis`, not `postgres`.

Seed demo users **inside the backend container** (no host Poetry required):

```bash
# Linux / macOS / Git Bash
bash scripts/seed_demo_compose.sh
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/seed_demo_compose.ps1
```

Equivalent: `docker compose exec -T backend python -m src.scripts.seed_rbac_baseline` then `… seed_multi_tenant_showcase`. Host Poetry against `localhost:5442` still works if you prefer. Optional heavier single-clinic seed: `seed_presentation_showcase` (do not mix with the multi-tenant showcase unless you intend to).

**Demo logins (local seeds only — never reuse in a real deployment):**

| Seed | Email | Password | Sign-in |
|---|---|---|---|
| Multi-tenant showcase | `owner.kazan@showcase-mt.demo` | `ShowcaseMT2026!` | `/admin/login` |
| Presentation clinic | `admin@dentapro.demo` | `Presentation2026!` | `/admin/login` |

Full tables: [`documentation/DEMO_CREDENTIALS.md`](./documentation/DEMO_CREDENTIALS.md).

### Host-run API + Vite (faster iteration)

```bash
docker compose up -d db redis
# create dental_booking and dental_booking_test once
docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"
cp .env.example .env
poetry install
poetry run alembic upgrade head
poetry run uvicorn src.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Vite is typically **5175** and proxies `/api` to host uvicorn **8000**, or Compose **8010** if 8000 is down. Details: [`documentation/GETTING_STARTED.md`](./documentation/GETTING_STARTED.md).

### Tests

```bash
poetry run pytest tests/ -q
cd frontend && npm test
```

`DATABASE_URL_TEST` must point at `dental_booking_test`. Stop compose `backend` / `celery` if they share the same Postgres — the instance `max_connections` is a shared budget.

---

## What to look at if you have ten minutes

This is the intended reading order for someone who arrived from [LEO](https://github.com/alex-zaporozhan/leo) or HN:

1. `src/application/booking_slot_advisory_lock.py` + `tests/core/test_booking_slot_policy_lock.py` — the double-booking class.
2. `src/application/rbac_matrix.py` + `tests/application/test_sec_rbac_router_permissions_inventory.py` — permission drift is a CI failure.
3. `src/application/multitenancy.py` + `tests/api/test_tenant_isolation_admin_paths.py` — tenant scope.
4. `src/api/v1/router.py` — **95** `include_router` mounts, one monolith.
5. `docs/adr/` — decisions with numbers, including [ADR-017](./docs/adr/ADR-017-source-available-polyform-shield.md) (why this is not MIT).

---

## Known limitations

Honesty is the point of publishing a debut.

- **First LEO run.** Later systems built under the same process are tighter. Do not treat this repo as the ceiling of the framework.
- **Tenant isolation** is application-layer + tests, not RLS-on-every-table.
- **Admin chrome** is mixed. Login, sidebar, schedule, feed/reports, omni, and Kanban **card/toolbar** are on i18n keys (`en` default). Landing `/`, signup, and owner-invite use `marketing`. Task **drawers** and many other admin bodies still have Russian literals. **Patient PWA** (`/app`, `/c/:slug`) shell, booking wizard, chat, profile, store, history, **loyalty / forms / clinic feed / booking-success** use the `patient` ns (English default). Template field labels and form names still come from the API. `/sandbox` and legal placeholders can still be Russian. Demo **seed data** (staff names, huddles, omni, catalog overlay, **±14-day EN window**: denser calendar, Kanban, meetings, doctor-role login) is English after `seed_multi_tenant_showcase` / `backfill_showcase_saas_extras`. Re-running the showcase seed on a marked DB applies extras **idempotently** (RU and EN title prefixes), refreshes the English video layer, then the two-week window. Demo rows are **not** Alembic migrations. Locale is `localStorage.ui.locale` **per origin** (`:3010` ≠ `:5175`). Collapsed 80px sidebar has no switcher — expand it first.
- **Payments / SMS / OAuth** adapters in the demo path are region-pluggable; the seeded path may assume a RU provider.
- **`EDITION=box|basic`** still exists as a compatibility SKU gate. Ignore it unless you are studying that cut.
- **Not OSI Open Source.** Source-available, PolyForm Shield — see below.

Gaps that are *not* hidden behind a badge belong in GitHub issues after the repo is public, not in a rewritten history.

---

## Documentation

| Doc | What |
|---|---|
| [`documentation/PRODUCT_OVERVIEW.md`](./documentation/PRODUCT_OVERVIEW.md) | Product contours and modules |
| [`documentation/ORIGIN.md`](./documentation/ORIGIN.md) | Why this repo exists, in full |
| [`documentation/GETTING_STARTED.md`](./documentation/GETTING_STARTED.md) | Clone → demo |
| [`documentation/DEMO_CREDENTIALS.md`](./documentation/DEMO_CREDENTIALS.md) | Seed logins (DEMO only) |
| [`documentation/LICENSING.md`](./documentation/LICENSING.md) | License in plain language |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | PR / test / config contract |
| [`SECURITY.md`](./SECURITY.md) | Private vulnerability reports |
| [`CI_CD.md`](./CI_CD.md) | Jenkins / GHCR / Docker Hub |

---

## License

**Source-available**, not OSI Open Source. SPDX: [`LicenseRef-PolyForm-Shield-1.0.0`](./LICENSE).

- You **may** read, run, study, fork for learning, and run this inside a clinic you operate.
- You **may not** offer a competing clinic OS / booking SaaS built from this software (hosted or on-prem).

That is the same family of license as [LEO](https://github.com/alex-zaporozhan/leo), for the same reason: use it, do not resell the product. Full comparison: [`documentation/LICENSING.md`](./documentation/LICENSING.md). Commercial exceptions: [LinkedIn](https://www.linkedin.com/in/alex-zaporozhan/).

---

## Author

**Alexandr Zaporozhan** — AI-native systems work; five years Emergency ICU before this; the person who wrote LEO because the market would not hand over a team.

- Framework: [github.com/alex-zaporozhan/leo](https://github.com/alex-zaporozhan/leo)
- [LinkedIn](https://www.linkedin.com/in/alex-zaporozhan/)

Open to Founding Engineer roles, AI-native full-stack seats, and AI-SDLC architecture contracts.

---

<div align="center">

*The interesting question is not whether an LLM can write a FastAPI handler.*
*It is whether a written process can keep the tenth month of that work from quietly contradicting the first.*

[LEO — the constitution this repo was built under →](https://github.com/alex-zaporozhan/leo)

</div>
