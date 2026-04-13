# ADR-009: Reliable domain event delivery (outbox)

- **Status:** Accepted (partial) — `domain_outbox` table, **PaymentSuccess** (contour A / patient webhook), **PlatformSignupProvision** (contour B), **booking lifecycle** events via transactional enqueue + dispatch; see `src/application/services/domain_outbox_service.py`.
- **Date:** 2026-04-03 (synced with implementation 2026-04-06)
- **Context:** In-process `EventBus` in `src/application/events/event_bus.py` does not span API replicas and is not atomic with the HTTP transaction (FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md §2.1). U-007.

## Decision (target)

1. **Outbox** table in the same database: id, aggregate_type, aggregate_id, event_type, payload, created_at, published_at, attempts, last_error, optional dedup_key.
2. Insert outbox rows in the **same transaction** as domain writes.
3. **Celery** task `domain_outbox.dispatch_pending` drains unpublished rows; HTTP paths may call `dispatch_domain_outbox_batch` **after commit** (post-commit dependency) for lower latency.
4. Handlers are **idempotent** where at-least-once applies (dedup_key / domain guards).

## Configuration (environment)

Settings live in `src/core/config.py` (Pydantic `Settings`); env names are **uppercase** with underscores (same as field names).

| Env / setting | Default | Role |
|---------------|---------|------|
| `DOMAIN_OUTBOX_PAYMENT_WEBHOOK_ENABLED` | `true` | After patient payment webhook commit, run post-commit `dispatch_domain_outbox_batch` (`get_session_payment_webhook_domain_outbox`). |
| `DOMAIN_OUTBOX_PLATFORM_BILLING_PROVISION_ENABLED` | `true` | Enqueue `PlatformSignupProvision` on platform billing success; dispatch runs after commit / Celery. |
| `DOMAIN_OUTBOX_BOOKING_EVENTS_ENABLED` | `true` | Booking mutations use transactional `enqueue_domain_event` instead of only in-process bus. |
| `DOMAIN_OUTBOX_DISPATCH_BATCH_LIMIT` | `50` | Max rows per `dispatch_domain_outbox_batch` call. |
| `DOMAIN_OUTBOX_METRICS_DB_REFRESH_MIN_INTERVAL_SECONDS` | `5` | Throttle DB reads when refreshing outbox gauges on `GET /metrics` (0 = refresh every scrape). |
| `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS` | `0` | If `>0`, rows with `attempts >= cap` are excluded from dispatch; gauge `domain_outbox_blocked_by_attempt_cap_rows`. |

See also `.env.example` (block **ADR-009 / domain outbox**).

## Metrics (`GET /metrics`)

Defined in `src/core/metrics.py` (low-cardinality; no per-tenant labels on gauges).

| Metric | Type | Meaning |
|--------|------|---------|
| `domain_outbox_dispatch_total{result,event_type}` | Counter | Dispatch outcomes per event type (`ok` / `error`). |
| `domain_outbox_post_commit_dispatch_failures_total{dependency}` | Counter | Post-commit drain raised after HTTP commit (`dependency=booking_routes` \| `payment_webhook`). |
| `domain_outbox_pending_rows` | Gauge | Count of rows with `published_at IS NULL`. |
| `domain_outbox_oldest_pending_age_seconds` | Gauge | Age of oldest unpublished row (0 if empty). |
| `domain_outbox_blocked_by_attempt_cap_rows` | Gauge | Unpublished rows blocked by attempt cap (0 if cap disabled). |
| `domain_outbox_gauge_refresh_failures_total` | Counter | DB errors while refreshing gauges. |

Gauges are refreshed from `refresh_domain_outbox_gauges` (called after batch dispatch and on metrics scrape when throttle allows).

## Prometheus alerts

In `deploy/prometheus/dental_booking_alerts.yml` (group **Phase 2 reliability**):

- **DomainOutboxOldestPendingStale** — `domain_outbox_oldest_pending_age_seconds > 600` (15m).
- **DomainOutboxPendingBacklog** — `domain_outbox_pending_rows > 50` (15m).
- **DomainOutboxBlockedByAttemptCap** — `domain_outbox_blocked_by_attempt_cap_rows > 0` (10m).
- **DomainOutboxPostCommitDispatchFailures** — `increase(domain_outbox_post_commit_dispatch_failures_total[10m]) >= 1` (5m).

Runbook pointers: `docs/architecture/arch_plan/07_PHASE_2_RELIABILITY.md`, `docs/operations/DR_RUNBOOK.md` (attempt-cap stuck rows).

## Celery

- Task name: **`domain_outbox.dispatch_pending`** (`src/infrastructure/messaging/tasks/domain_outbox_tasks.py`), scheduled in `celery_app` beat for crash recovery and multi-replica.

## Dispatch behaviour (fact)

- **`PlatformSignupProvision`:** handled inline in `dispatch_domain_outbox_batch` (`_dispatch_platform_signup_provision_row`); not republished to `EventBus` in the same way as serialized `DomainEvent` rows.
- **Other `event_type`:** payload deserialized via `_event_from_payload` → `EventBus.publish`.

## Test coverage (2-F5 tail)

Automated tests (idempotency / redelivery):

- **PaymentSuccess path:** `tests/application/test_domain_outbox_payment.py`.
- **PlatformSignupProvision:** `tests/application/test_domain_outbox_platform_provision.py` (`test_platform_webhook_outbox_row_published_and_provisioned`, `test_dispatch_platform_outbox_redelivery_no_extra_org_rows`, …).
- **Booking lifecycle enqueue + dedup + simulated redelivery:** same file — `test_booking_outbox_dedup_and_second_dispatch_empty`, `test_booking_outbox_redelivery_republishes_event`.

No additional outbox **event types** are dispatched beyond the above in code today; new types should add tests in the same style before marking backlog **2-F5** done for those types.

## Consequences

Alembic migration `20260414_phase2_domain_outbox`, idempotent consumers, metrics and alerts above (QA_ARCH Phase 2).

## Links

- U-007; `docs/architecture/domains/booking_event_chain.md`
- Module runbook (contour B + outbox cross-ref): `docs/architecture/modules/platform_subscription_billing.md` §10
- **Отчёт приёмки (поток epics):** [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md), [STREAM_PHASE2_RELIABILITY_EPICS.md](../architecture/arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md), [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (**2-F***).

## Outstanding (partial acceptance)

Статус *partial* снимается после закрытия оставшихся строк **2-F3 / 2-F4 / 2-F7** и прочих эпиков вне Wave 1 в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (отдельные тикеты по плану LEAD). **2-F6** (синхронизация ADR с фактом) — этот документ; **2-F5** хвост для существующих типов — покрыт тестами выше.
