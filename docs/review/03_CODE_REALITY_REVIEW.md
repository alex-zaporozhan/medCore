# Code Reality Review (Implementation vs Enterprise SaaS Quality)

This review is code-first. Documentation claims are accepted only when supported by code, tests, and executable operational behavior.

## 1) Implemented (strong evidence)

### A. Platform billing contour B baseline

- Separate B webhook path, dedicated secret checks, and billing domain services are present.
- Signup intent/payment persistence and provisioning flow are implemented.
- Entitlement assignment and owner invite flow exist in code paths.

### B. Webhook A/B separation

- Patient payment and platform billing use separate route spaces and separate secret handling logic.

### C. Entitlement routing implementation

- Router-level entitlement dependencies are widely present in optional modules.
- Inventory + check script + CI workflow exist for entitlement coverage.

### D. Security/abuse metrics baseline

- Security and spam counters are present with low-cardinality intent.
- Platform billing webhook metrics include result labels.

### E. Outbox foundation

- Domain outbox entities/services/tasks/metrics are present.
- Booking/payment/platform provisioning hooks reference outbox dispatch logic.

## 2) Partially implemented (not production-complete)

### A. Retry/DLQ/reconcile maturity for post-payment failures

- There is meaningful implementation, but operational completeness is not yet at strict enterprise closure level.
- Needs end-to-end operator-grade closure with staging proof and hard acceptance.

### B. Founder production secret model

- Runtime secret loading support exists, but readiness indicates production hardening still in progress.
- Current model still permits env-heavy operation patterns.

### C. Multi-replica reliability governance

- Outbox exists, but safe operation depends on strict operational enablement and runbook discipline.
- Must enforce one explicit policy path for replicas and public money paths.

### D. Anti-spam completeness

- Major controls exist (rate limits, captcha-related components, suspicious event tracking).
- Coverage must be verified as complete across all sensitive public and admin surfaces.

### E. CI depth for regression containment

- Release gate (`release-gate.yml`) остаётся полным; PR job `build-and-test-entitlements.yml` **verify** дополнен обязательным прогоном `tests/core/test_payment_webhook_governance.py` и `tests/api/test_platform_billing.py` (DEV execution plan baseline / WP5.1). Disabled workflows — по политике команды (см. `.github/workflows/`).

## 3) Critical production risks

1. **Security hardening gap risk**  
   Production secrets and secret lifecycle controls are not fully closed at readiness level.

2. **Operational consistency risk**  
   Some advanced recovery paths are implemented but not fully proven as stable operator flow in production-like routine.

3. **Isolation confidence risk**  
   Isolation quality improved materially, but must be continuously validated at DB+app boundary for enterprise claims.

4. **Legacy enforcement gap**  
   Legacy entitlement behavior can undermine strict commercial gating if migration/backfill governance is weak.

5. **Public-edge abuse risk**  
   Public endpoints are protected better than before, but enterprise-grade closure requires complete and continuously validated anti-abuse coverage.

## 4) "Done/Partial/Missing" summary

| Capability | Status |
|---|---|
| Contour B base flow | DONE |
| A/B webhook separation | DONE |
| Provisioning with entitlements and owner invite | DONE |
| Retry/DLQ/reconcile full closure | PARTIAL |
| Founder secret hardening in production | PARTIAL |
| Outbox + replicas enterprise closure | PARTIAL |
| Entitlement gating full migration safety | PARTIAL (**регрессии WP3.2:** `ensure_org_entitlement_keys_for_public_client`, `ensure_org_has_any_entitlement_for_organization`, режим `legacy`) |
| Anti-spam complete closure | PARTIAL |
| Observability hardening closure | PARTIAL (**PRC-F2:** `runbook_url` добавлены для ряда правил в `deploy/prometheus/dental_booking_alerts.yml`; cardinality/OPS-proof — вне репозитория) |
| CI full-depth quality gate | PARTIAL (**WP5.2:** [CI_WORKFLOWS_WAIVERS.md](../architecture/arch_plan/CI_WORKFLOWS_WAIVERS.md); PR verify — webhook governance + contour B billing) |

## 5) Risk -> WP -> PRC traceability matrix

This matrix links every `PARTIAL`/risk area to executable work packages from
`docs/review/04_DEV_EXECUTION_PLAN.md` and closure target in PRC.

Legend:
- `Criticality`: `P0` (release-blocking) / `P1` (high, non-immediate release stop)
- `Target state`: what must be true to move from PARTIAL to DONE

| Risk / Gap | Criticality | Current state | Linked WP | PRC rows to close/keep | Target state |
|---|---|---|---|---|---|
| Founder production secret hardening | P0 | Runtime secret support exists, but production hard closure incomplete | `WP1.1`, `WP1.2` | `PRC-A3` | Production cannot start with missing critical secrets; founder auth policy enforced by code and tests |
| Public-edge anti-abuse coverage incompleteness | P0 | Controls exist but completeness not fully proven for all sensitive paths | `WP1.3` | `PRC-C1` (security part), `PRC-B7` | Sensitive public paths have explicit protection matrix + negative tests + observable rate-limit behavior |
| Retry/DLQ/reconcile not fully operator-closed | P0 | Core mechanics present, enterprise operational closure not finished | `WP2.1`, `WP2.2` | `PRC-B4` | Deterministic failure states + safe retry/reconcile path proven end-to-end |
| Refund/chargeback lifecycle not fully closed in code | P0 | Partial implementation, full ADR-012 lifecycle closure pending | `WP2.4` | `PRC-B5` | Refund/chargeback outcomes are terminally consistent and idempotent |
| Outbox/replica safety depends on ops discipline | P0 | Outbox exists, but runtime policy closure remains partial | `WP2.3` | `PRC-E1`, `PRC-E3` | Replica-safe operation and eventual recovery proven under failure/redelivery scenarios |
| Legacy entitlement enforcement ambiguity | P1 | Strong entitlement gating exists, but legacy mode can stay permissive | `WP3.1`, `WP3.2`, `WP3.3` | `PRC-D1`, `PRC-D2` (must remain satisfied) | Legacy cohort behavior is explicit, migrated, and protected by regression tests |
| Observability hardening incomplete | P1 | Metrics/alerts exist; cardinality and incident readiness closure incomplete | `WP4.1`, `WP4.2`, `WP4.3` | `PRC-F1`, `PRC-F2`, `PRC-F3`, `PRC-G2` | Alerting and dashboards support actionable incident triage with low-cardinality guarantees |
| CI depth and workflow debt | P1 | Release gate exists; PR-level critical coverage is incomplete | `WP5.1`, `WP5.2`, `WP5.3` | `PRC-E4` (keep), release policy rows | Critical domains are guarded by mandatory PR suite and release guardrails |

## 6) Execution mapping by PARTIAL capability

| PARTIAL capability | WP mapping | PRC mapping | Closure evidence required |
|---|---|---|---|
| Retry/DLQ/reconcile full closure | `WP2.1`, `WP2.2` | `PRC-B4` | Failing-path tests, reconcile flow proof, runbook-linked alerts |
| Founder secret hardening in production | `WP1.1`, `WP1.2` | `PRC-A3` | Fail-closed startup behavior + auth policy tests + ops checklist update |
| Outbox + replicas enterprise closure | `WP2.3` | `PRC-E1`, `PRC-E3` | Redelivery/failure-recovery tests + operational decision evidence |
| Entitlement gating full migration safety | `WP3.1`, `WP3.2`, `WP3.3` | `PRC-D1`, `PRC-D2` | Legacy migration report + bypass regression suite + UI/API parity checks |
| Anti-spam complete closure | `WP1.3` | `PRC-C1`, `PRC-B7` | Protection matrix + abuse tests + rate-limit metrics/alerts evidence |
| Observability hardening closure | `WP4.1`, `WP4.2`, `WP4.3` | `PRC-F1`, `PRC-F2`, `PRC-F3`, `PRC-G2` | Staging smoke, cardinality proof, owner/runbook completeness |
| CI full-depth quality gate | `WP5.1`, `WP5.2`, `WP5.3` | `PRC-E4` and release guardrails | Critical suite policy in CI + workflow debt resolved/waived explicitly |

## 7) Priority queue for implementation

Recommended strict execution order (risk-first):

1. `WP1.1` -> `WP1.2` -> `WP1.3`
2. `WP2.1` -> `WP2.2` -> `WP2.3` -> `WP2.4`
3. `WP3.1` -> `WP3.2` -> `WP3.3`
4. `WP4.1` -> `WP4.2` -> `WP4.3`
5. `WP5.1` -> `WP5.2` -> `WP5.3`

No step is considered done without synchronized PRC status update and evidence links.

## 8) Quality conclusion

Project is significantly beyond "paper MVP" and has real enterprise-grade building blocks in code.  
However, it is not yet at "no-formalism, fully production-closed" target because several PARTIAL domains remain in security, reliability, and operational closure.

## 9) Phase 1 execution evidence update

Validated during implementation:

- `pytest tests/core/test_payment_webhook_governance.py -q` -> passed
- `pytest tests/api/test_platform_internal.py -q` -> passed
- `pytest tests/api/test_phase1e_embed.py -q` -> passed
- `poetry run pytest tests/api/test_platform_billing.py -q` -> passed

Important finding:

- `prometheus-client` was already declared in `pyproject.toml`; test failure occurred when running outside Poetry environment.
- Evidence policy updated in `docs/review/04_DEV_EXECUTION_PLAN.md` to require `poetry run pytest` for backend closure proof.
