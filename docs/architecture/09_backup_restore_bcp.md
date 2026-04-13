# Backup, restore, BCP

**Status:** cluster backup = OPS/managed DB; app exposes **optional** Prometheus metrics for admin JSON logical export (`backup_logical_export_*`, Celery) — см. [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) §8.  
**ADR:** [ADR-008](../adr/ADR-008-backup-restore-bcp.md) (partial Accepted).  
**Runbook:** [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md).  
**Target platform:** [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](./TARGET_PLATFORM_MULTITENANCY_REFERENCE.md).

## Purpose

Enterprise expectations for PostgreSQL continuity. Distinguish:

- Cluster backup: disaster recovery for whole service.
- Tenant export: per-organization logical export (app-level, contractual).

## Recommended production

1. Managed Postgres: snapshots plus PITR where available; retention policy.
2. Encrypted logical dumps to object storage; KMS separate from app secrets.
3. Restore drills on staging; track duration and success (QA_ARCH Week 4).

## Local docker-compose

Volume `pgdata` is not a production policy; see DR_RUNBOOK for team notes.

## Enterprise audit

- Critical: without managed backup and drills, RPO/RTO are only intent.
- Follow ADR-008 and U-009; отложенная работа по фазе 2 — **[2-F2, 2-F4](arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md)**.

### PRINCIPLE

See [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) and BCP in [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).
