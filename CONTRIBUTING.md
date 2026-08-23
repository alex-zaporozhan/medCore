# Contributing

Public documentation policy: [`DOCUMENTATION_POLICY.md`](./DOCUMENTATION_POLICY.md).

**CI/CD:** single-VPS / demo default is a local image build and **Docker Hub** (`scripts/docker_hub_release.ps1` / `.sh`, see [`CI_CD.md`](./CI_CD.md)). Org pipeline is **Jenkins + GHCR**. GitHub Actions are PR gates and an optional Hub publish when secrets exist.

This codebase was built under [LEO](https://github.com/alex-zaporozhan/leo). You do not need LEO to send a patch. You do need tests for the behavior you change.

## Pull requests

1. **Traceability** — Link the issue or task id and the acceptance criterion you implemented.
2. **Tests** — Run pytest / vitest for modules you touched (full suite if you can). Test DB: [`documentation/GETTING_STARTED.md`](./documentation/GETTING_STARTED.md), [`documentation/DEVELOPMENT.md`](./documentation/DEVELOPMENT.md); `tests/conftest.py` (`DATABASE_URL_TEST`, `dental_booking_test`).
3. **Config** — New env vars go in `.env.example` and in operator-facing notes.
4. **NFR** — If metrics, alerts, or dashboards change, update [`documentation/OBSERVABILITY.md`](./documentation/OBSERVABILITY.md).

GitHub shows `.github/pull_request_template.md` on new PRs.

## API: partial updates (PUT/PATCH)

One contract for admin PUT and PATCH bodies:

- Pass **`body.model_dump(exclude_unset=True)`** (or equivalent) into the service so omitted fields are not overwritten with `None` / defaults.
- Full-replace DTOs are a separate agreement. Optional fields prefer PATCH + `exclude_unset`.

## Errors

API errors use `{"detail": "...", "code": "SNAKE_CASE"}`. A bare 500 without that envelope is a bug.

## Supply chain (backend)

JWT: **PyJWT** only (`src/core/security.py`), not `python-jose`. After dependency edits run `poetry sync` so stale transitive packages do not linger. Release audits follow the `Jenkinsfile` and workflows under `.github/workflows/`.

## RBAC

`documentation/rbac_router_permissions.txt` must match `require_permissions` calls in `src/api/v1/routers/`.

```bash
python scripts/audit_rbac_endpoints.py --check
```

CI: `pytest tests/application/test_sec_rbac_router_permissions_inventory.py`.

## Local hooks (optional)

```bash
git config core.hooksPath .githooks
```

`pre-commit` is a fast gate; `pre-push` is the full quality gate. Direct push to `main` is blocked unless `ALLOW_MAIN_PUSH=1`.
