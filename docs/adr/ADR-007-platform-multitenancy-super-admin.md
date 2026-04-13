# ADR-007: Platform multi-tenancy, super-admin, self-service business

- **Status:** Proposed — **Phase 0 (2026-04-05): fork изоляции зафиксирован** (см. ниже); остальные пункты (JWT platform, self-service, super-admin UI) остаются в дорожной карте §15 / Фаза 1a+.
- **Date:** 2026-04-03
- **Context:** Data isolation today relies on `clinic_id` in application code. There is no platform-operator contour or self-service signup for a new SaaS business tenant (see U-004 and TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).

## Phase 0 supplement — data isolation fork (binding for Phase 1a)

Per [01_PHASE_0_PREPARATION.md](../architecture/arch_plan/01_PHASE_0_PREPARATION.md) and [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §19:

1. **Chosen execution track until an explicit RLS epic:** **Option B** — strict application-layer scoping (`organization_id` / `clinic_id` in repositories and services) plus **mandatory cross-tenant negative tests** for any new code that touches platform tables or crosses tenant boundaries.
2. **Option A (PostgreSQL RLS)** remains the **target** for Enterprise-grade hardening; adopting RLS requires a follow-up amendment to this ADR (schema strategy, rollout, performance review) and is **not** assumed for the first platform migrations unless LEAD/ARCH re-open the fork.

### Amendment (2026-04-06) — partial RLS on `organization_entitlements`

Migration `20260423_phase1a_founder_totp_org_ent_rls` enables **RLS + FORCE** on `organization_entitlements` with a **GUC-gated** policy: when `app.rls_org_entitlements` is unset or not `'on'`, all rows pass (application-layer remains primary). When a session sets `app.rls_org_entitlements = 'on'` and `app.effective_organization_id` to a UUID, only matching rows are visible — used for **defence-in-depth** and pytest verification ([QA_REPORT_1a_E5_rls](../artifacts/QA_REPORT_1a_E5_rls.md)). Broader RLS on tenant tables remains a separate Enterprise epic.

## Decision (target)

1. Explicit model: **Platform** vs **Organization (business tenant)** vs **Clinic**.
2. JWT and RBAC distinguish **platform roles** (support, billing, security read-only, super-admin) from **tenant clinic admin** roles.
3. **Self-service onboarding:** organization registration, first owner, clinic creation; rows carry `organization_id` and `clinic_id` where applicable.
4. **Super-admin (vendor):** separate issuer/claim or realm; never ambiguous with clinic `AdminUser` without audit trail.
5. **Platform powers (minimum):** suspend/enable organization, aggregated metrics/errors view, **tenant data export** on request, plan feature flags; revocation via platform RBAC and audit log.

## Data isolation fork

- **Option A (preferred for Enterprise):** PostgreSQL **RLS** on `organization_id` / `clinic_id` with per-request context.
- **Option B:** strict application policy layer plus mandatory cross-tenant negative tests on all repos.

## Consequences

Schema migrations, platform audit tables, separate admin UI or shell section. Legal constraints on PII in logs are out of scope of this ADR but affect masking.

## Links

U-004, U-005; FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md section 3 (RLS).
