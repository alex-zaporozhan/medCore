# Contributing

## Pull requests (QA_ARCH / `DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG` §5)

When closing backlog items from `docs/artifacts/QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md` or related `ARCH_DEV_*_TASKS.md`:

1. **Traceability** — In the PR description, link the **ID** (e.g. A7, W1.1) and the **section or line** in the source TASK file or the unified backlog.
2. **Tests** — Run and note `pytest` / `vitest` for **modules you touched** (full suite if feasible).
3. **Config** — New env vars: `.env.example` and `docs/MIGRATION_UPGRADE.md` when operators must act.
4. **NFR** — If metrics, alerts, or runbooks change, update `docs/artifacts/NONFUNCTIONAL_AUDIT_NEXT.md` as needed.

GitHub will show `.github/pull_request_template.md` when opening a PR.
