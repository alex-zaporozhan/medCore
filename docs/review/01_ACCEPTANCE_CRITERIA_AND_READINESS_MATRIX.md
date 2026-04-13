# Acceptance Criteria and Readiness Matrix

## 1) Non-negotiable acceptance criteria

### A. System integrity

- Every capability must be end-to-end functional (API + domain logic + UI path where required).
- No "doc-only" closure for production claims.
- No hidden manual dependency for core money/auth/provisioning paths unless explicitly marked as temporary risk with owner and expiry date.

### B. Functional completeness

- Critical journeys must run without manual patching:
  - founder auth and access recovery
  - plan selection and checkout
  - webhook processing
  - provisioning
  - entitlement enforcement
  - operational recovery (retry/reconcile)
- Frontend must expose operational controls for required flows (not API-only where operations depend on it).

### C. Security completeness

- Isolation must be enforced in both application and data layers for sensitive boundaries.
- Auth realms must be separated for founder and tenant/admin.
- Public endpoints (signup/webhooks/embed) must have anti-abuse controls.
- Secrets in production must be managed via secure runtime source, not static env-only model.

### D. Reliability completeness

- Idempotency for public money/event flows.
- Retry + dead-letter + operator reconcile for post-payment failures.
- Replicas/outbox policy explicitly enforced for public money flows.
- Alerts and metrics must cover failure states, not only happy-path counters.

### E. Operational completeness

- DR, backup drill evidence, release gate evidence, and runbook links are mandatory.
- Production claims require artifacted status in readiness matrix, not chat claims.

## 2) Functional "fully done" definition

A capability is "fully done" only when all are true:

1. Business flow works end-to-end.
2. Negative paths are handled (invalid payload, duplicate events, retries, stale states).
3. Operator path exists (diagnose, recover, reconcile).
4. Security controls exist and are tested.
5. Observability exists (metrics + alert thresholds + runbook reference).
6. CI checks block regressions for the capability.

## 3) Security acceptance criteria

- Identity separation: founder realm and tenant/admin realm cannot impersonate each other.
- Tenant isolation: no cross-tenant data leakage by API, queries, or metrics labels.
- Public edges: rate limiting and abuse controls active for signup/webhook/embed/login.
- Secrets: runtime secure loading for production, with audited fallback policy.
- Error discipline: no stack or sensitive internals in client-facing production errors.

## 4) Readiness matrix (code-first)

Legend:
- `DONE` = implemented and evidenced in code/tests
- `PARTIAL` = implemented in part; production quality incomplete
- `MISSING` = not implemented to required level

| Domain | Status | Notes |
|---|---|---|
| Founder realm and 2FA | PARTIAL | Implemented, but production secret hardening still incomplete at readiness level |
| Billing contour B core (checkout/webhook/provisioning) | DONE/PARTIAL | Core flow done; advanced failure mechanics and operational closure still partial |
| Webhook A/B separation | DONE | Separate paths/secrets and tests present |
| Provisioning completeness (owner + entitlements) | DONE | Present in code path and tests |
| Retry/DLQ/reconcile (C2) | PARTIAL | Present in part; not fully closed for production runbook maturity |
| Outbox/replica-safe operation | PARTIAL | Implemented, but operational enforcement and full closure still pending |
| Entitlement gating | PARTIAL | Strong implementation, but legacy non-enforced organizations remain risk surface |
| Anti-spam and abuse controls | PARTIAL | Good controls exist; not uniformly proven complete across all sensitive surfaces |
| Observability and alerting maturity | PARTIAL | Metrics and alerts exist; production hardening and cardinality proof still open |
| DR/BCP execution maturity | PARTIAL | Documents and partial evidence exist; full closure requires repeated operational evidence |
| CI gate strength | PARTIAL | Release gate exists; PR-level breadth still limited in places |

## 5) Production quality threshold

Project is considered production-ready only when:

- all critical matrix rows move from `PARTIAL/MISSING` to `DONE`,
- no critical security/reliability exception remains without owner+deadline+waiver,
- readiness tracker reflects the same reality as code and tests.
