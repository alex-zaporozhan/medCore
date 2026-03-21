## Backlog / scope

- **IDs (QA_ARCH / TASK):** <!-- e.g. A7, W1.1 — link to `docs/artifacts/QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` or `ARCH_DEV_*_TASKS.md` §… -->

## Checklist

- [ ] Links above point to the **exact** TASK section or unified backlog row
- [ ] `pytest` / `vitest` run for **touched** areas (or full CI green)
- [ ] New env vars documented in `.env.example` (+ `docs/MIGRATION_UPGRADE.md` if needed)
- [ ] NFR / alerts / metrics updated if applicable (`docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md`)
- [ ] **Frontend / admin UI:** new right-hand detail panels use `AdminDrawer` from `@/shared/ui`, not raw `Drawer` from `@mantine/core` (`adminNoRawMantineDrawer` test)

## Notes

<!-- Optional: rollout, feature flags, OPS -->
