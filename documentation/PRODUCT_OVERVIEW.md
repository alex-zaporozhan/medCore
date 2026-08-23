# MedCore — product overview

**MedCore** (repository folder: `dental_booking`) is a multi-tenant clinic operating system, dental vertical first. One modular monolith: REST API, staff admin, patient PWA, public signup, and a vendor/founder contour.

This page is the public product map. If a sentence here disagrees with the code, the code wins.

## Contours

| Contour | Audience | Routes | Auth |
|---|---|---|---|
| Marketing / signup | Incoming organizations | `/`, `/signup` | Public |
| Clinic admin | Staff | `/admin/*` | Admin JWT + RBAC |
| Patient | Patients | `/c/:clinicSlug/*`, `/app/*` | Patient JWT / OTP |
| Platform | Vendor / founder | `/platform/*` | Separate founder JWT realm |

Tenancy: **Platform → Organization → Clinic**. Isolation is application-layer scoping plus cross-tenant tests; RLS is selective, not universal. See [ADR-007](../docs/adr/ADR-007-platform-multitenancy-super-admin.md).

## What ships in the tree

Verified against routers, pages, and tests — not a TAM slide.

- **Booking and schedule** — public and staff booking, doctor calendars, waitlist, advisory-locked slot contention.
- **Directory** — patients, doctors, services, clinics, administrators.
- **CRM** — leads, pipeline, recall, marketing attribution.
- **Tasks** — Kanban boards, assignment, clinic vs personal boards.
- **Omnichannel** — operator inbox, channel config, staff chat, patient chat.
- **Money inside the clinic** — payments (pluggable gateway), prepayment, finance, inventory, payroll, discounts, loyalty.
- **Platform money** — catalog, checkout, provision queue, founder ops. Separate webhook secret from clinic-side payments.
- **Entitlements** — organization feature flags; admin nav hides what the plan does not include.
- **RAG knowledge base** — org-scoped, config-gated.
- **Observability** — `/health`, `/health/replica`, `/metrics`, compose profile `observability`.

Admin login routes default to **English** (i18next). The **public landing** `/` and **signup** `/signup` follow `ui.locale` (`marketing` ns; default `en`), including checkout chrome and plan overlay strings. Catalog API `display_name` may still be Russian. `index.html` first paint is `lang="en"` / MedCore. The staff **shell** (nav groups, home/logout, locale switch) follows `ui.locale`. The switch lives in the **expanded sidebar**; when the navbar is collapsed to the 80px rail it moves to the top of Main (not duplicated). Founder `/platform/*` after login has the same control next to logout. Schedule, feed, reports, and omni inbox/composer chrome are on keys. Many other admin page bodies and drawers may still be Russian. There is no separate `AppShell.Header`.

## Stack (short)

Python 3.11 · FastAPI · SQLAlchemy 2 async · PostgreSQL 16 · Redis · Celery · React 18 · Vite 6 · Mantine 7 · TanStack Query 5.

Full table: root [`README.md`](../README.md#stack).

## Related public docs

| Doc | Use |
|---|---|
| [`ORIGIN.md`](./ORIGIN.md) | Why this repo is public |
| [`GETTING_STARTED.md`](./GETTING_STARTED.md) | Run it |
| [`DEMO_CREDENTIALS.md`](./DEMO_CREDENTIALS.md) | Seed logins |
| [`LICENSING.md`](./LICENSING.md) | PolyForm Shield in plain language |
| [`USER_DOCS/INDEX.md`](./USER_DOCS/INDEX.md) | End-user guides (mixed language) |

Built under **[LEO](https://github.com/alex-zaporozhan/leo)**.
