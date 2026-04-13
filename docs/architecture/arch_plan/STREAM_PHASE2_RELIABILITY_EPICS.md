# Поток Phase 2 — Надёжность (outbox, CI, DR)

> **МП:** [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md), ADR-008, ADR-009, **§17.1**.  
> **Долг:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **2-F1** … **2-F8**.  
> **Индекс:** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).  
> **PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-E1…E4**.

## QA_ARCH: префлайт для @ARCH и приёмка

**Цикл:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md). Инспектор: [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **ADR:** [ADR-008](../../adr/ADR-008-backup-restore-bcp.md), [ADR-009](../../adr/ADR-009-async-outbox-event-delivery.md).  
**Повторная приёмка потока 2-E1…2-E4 (после @DEV):** [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**2-F***), ADR-008/009.

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до @DEV** | **2-E1:** какой **hot-path** попадает в outbox (таблица/очередь), семантика **at-least-once**, кто consumer, связь с webhook B и **§17.1**. **2-E2:** границы цепочки booking + идемпотентность consumer. **2-E3:** список **имён workflow/jobs** U-008, что считается «зелёным» pipeline для релиза. **2-E4:** сценарий drill, RTO/RPO ссылка, ответственный, куда вносится дата учения. |
| **Минимум в `QA_REPORT`** | Тест **redelivery** или документированный прогон; для CI — ссылка на успешный run; для DR — **дата** в [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) или приложенный лист учения. |
| **Красные флаги** | Outbox «в теории» без метрики lag; включение CI без исключения flaky; DR только в тексте без даты drill; **две реплики API** без записи в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md). |

## Срезы

**2-E1** — Outbox или эквивалент на hot-path провижининга B при replicas≥2. DoD: запись в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) и код или явный operational режим.

**2-E2** — Outbox на цепочки booking. DoD: см. [booking_event_chain.md](../domains/booking_event_chain.md); идемпотентные consumer’ы; тесты redelivery.

**2-E3** — CI U-008: включение отключённых workflow по решению LEAD. DoD: документированный набор jobs; зелёный pipeline.

**Факт кода (2026-04-06, Phase 0 / @DEV):**

- Релизный gate: [`.github/workflows/release-gate.yml`](../../../.github/workflows/release-gate.yml) — `workflow_dispatch`, push тегов `v*`; entitlements-скрипт, сборка фронта, `phase0_governance_preflight.py all`, `pytest tests/`. **2-F8 / PRC-E4:** закрыто политикой LEAD [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](../../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md) (e2e/security из `workflows_disabled` — явный waiver до отдельного включения).
- **2-E3 / U-008:** [`.github/workflows/build-and-test-entitlements.yml`](../../../.github/workflows/build-and-test-entitlements.yml) — `verify`, `full-backend-tests`; [`.github/workflows/security-trivy.yml`](../../../.github/workflows/security-trivy.yml) — job `trivy-fs` (включён из `workflows_disabled`; на PR не блокирует merge при CRITICAL — см. `exit-code` в workflow).
- DR restore в CI: [`.github/workflows/dr-restore-drill.yml`](../../../.github/workflows/dr-restore-drill.yml) — только `workflow_dispatch` (OPS); не снимает обязанность **квартального** drill на staging + дата в [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) (**2-F2**).

**2-E4** — DR drill U-009. DoD: дата учения, ответственный, ссылка в [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md) и [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md).

---

**Версия:** 2026-04-07 (доп. U-008/U-009 — 2026-04-06).
