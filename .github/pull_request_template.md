## Backlog / scope

- **IDs / issue:** <!-- e.g. #123, TASK-… -->

## Checklist

- [ ] PR description links the **exact** task or acceptance criteria
- [ ] **Backend:** CI green if `src/`, `tests/`, or `pyproject.toml` / `poetry.lock` changed (GitHub Actions + local hooks; **release images/deploy = Jenkins** — see `CI_CD.md`)
- [ ] `pytest` / `vitest` run for **touched** areas (or full CI green)
- [ ] New env vars in `.env.example` (+ operator notes per team process)
- [ ] Metrics / alerts / dashboards updated if applicable (`documentation/OBSERVABILITY.md` for repo paths; internal NFR log per team)
- [ ] **Frontend / admin UI:** new right-hand detail panels use `AdminDrawer` from `@/shared/ui`, not raw `Drawer` from `@mantine/core` (`adminNoRawMantineDrawer` test)

## Notes

<!-- Optional: rollout, feature flags, OPS -->
