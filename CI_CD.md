# CI/CD

## Single-VPS / demo (default)

Build both images **locally**, confirm `docker build` succeeds, then `docker login` (password or token only at the terminal prompt) and `docker push` to **Docker Hub**.

Scripts from the repo root:

- Windows: `scripts/docker_hub_release.ps1` (`-Tag`, optional `$env:DOCKERHUB_USERNAME`).
- Linux / macOS: `scripts/docker_hub_release.sh` (`DOCKERHUB_USERNAME=... ./scripts/docker_hub_release.sh <tag>`).

On the VPS, set in `.env` for example `BACKEND_IMAGE=docker.io/<user>/dental-booking-backend:<tag>` and the matching frontend image. See [`documentation/VPS_IMAGE_AND_DATA.md`](./documentation/VPS_IMAGE_AND_DATA.md).

**GitHub Actions → Hub** needs repo secrets `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` (**Settings → Secrets and variables → Actions**). Workflow [`.github/workflows/docker-hub-publish.yml`](./.github/workflows/docker-hub-publish.yml):

- `workflow_dispatch` (tag field, default `main`);
- push / merge to `main` / `master` (images tagged `main`, path filters in the YAML);
- push of a `v*` git tag (image tag = git tag name).

Both images **build before login**, so a failed build never reaches push. Without secrets the job fails — use the local `scripts/docker_hub_release.*` helpers instead.

### Pytest gates vs image publishing

[`.github/workflows/docker-hub-publish.yml`](./.github/workflows/docker-hub-publish.yml) and [`.github/workflows/docker-images-build-verify.yml`](./.github/workflows/docker-images-build-verify.yml) run **`docker build` only** (and push when secrets exist). They **do not run pytest** and **do not read** production data.

Red checks usually come from other workflows: [`backend-ci.yml`](./.github/workflows/backend-ci.yml), [`build-and-test-entitlements.yml`](./.github/workflows/build-and-test-entitlements.yml), [`critical-path-gate.yml`](./.github/workflows/critical-path-gate.yml) (hard merge block — `pytest -m critical_path` must report 0 skips / errors / failures), [`release-gate.yml`](./.github/workflows/release-gate.yml), [`security-trivy.yml`](./.github/workflows/security-trivy.yml), and a `workflow_dispatch`-only [`dr-restore-drill.yml`](./.github/workflows/dr-restore-drill.yml) (ADR-008: prove a Postgres backup actually restores). Those spin up Postgres / Redis as CI **services** against an **empty** test database seeded by fixtures (`tests/conftest.py`). Typical CI does **not** need a live production DB or real third-party API keys. If the same tests fail locally, the usual causes are a missing `DATABASE_URL_TEST`, Redis, `FRONTEND_E2E_URL` for Playwright, or a connection-pool clash with a running API — see [`documentation/DEVELOPMENT.md`](./documentation/DEVELOPMENT.md).

**Publish images without waiting on pytest:**

1. **Local:** `scripts/docker_hub_release.ps1` / `.sh` — build + push, no pytest.
2. **GitHub:** **Actions → Docker Hub publish → Run workflow** (`workflow_dispatch`) on the branch / tag you want, with secrets set. That job builds images even if the last `backend-ci` on a PR was red (it is a **separate** workflow).
3. If **branch protection** requires `backend-ci` / `critical-path-gate`, merge to `main` will still wait on green checks — that is org policy, not the image YAML. Then either fix tests / infra, temporarily relax required checks (owner), or push images from **manual dispatch** without waiting for merge.

Do **not** maintain a repo-wide test allowlist to skip the gate. Point fixes are fine: `@pytest.mark.skip` / `xfail` with a ticket link, mocks for external APIs, or a separate `integration` marker and a workflow that omits it — by team decision.

**Local `pytest -m critical_path`:** if a Playwright smoke is selected and `FRONTEND_E2E_URL` is unset, tests start `vite preview` on `127.0.0.1:4173` (and `npm run build` in `frontend/` if needed). Disable that autostart with `PYTEST_DISABLE_VITE_AUTOSTART=1`.

## Image smoke without push or secrets

[`.github/workflows/docker-images-build-verify.yml`](./.github/workflows/docker-images-build-verify.yml) — `docker build` only (`push: false`), including on forks.

## Corporate pipeline: Jenkins and GHCR

When Jenkins is the org standard: build, publish, and deploy to the VM from the root [`Jenkinsfile`](./Jenkinsfile). Images go to **GitHub Container Registry (`ghcr.io`)** — see `GHCR_*` / `BACKEND_IMAGE_REPO` / `FRONTEND_IMAGE_REPO`. Registry credentials and SSH live **in Jenkins**, not in git. No paid Docker Hub tier is required on that path.

GitHub Actions under `.github/workflows/` are supplementary PR gates (tests, links, Trivy, and so on). They **do not replace** Jenkins when that pipeline is configured, unless a team runs Hub + Compose only.

## Local gates

Pre-commit / pre-push (`.githooks`) — a fast check before push.

### Dependencies: outdated packages and pip-audit (outside CI)

[`scripts/dev/check_dependency_updates.py`](./scripts/dev/check_dependency_updates.py) is a manual review helper. It does **not** replace the required `pip-audit` step in [`backend-ci.yml`](./.github/workflows/backend-ci.yml), but it is useful before a version bump.

```bash
poetry run python scripts/dev/check_dependency_updates.py
# poetry show --outdated; npm outdated in frontend/ if npm is on PATH

poetry run python scripts/dev/check_dependency_updates.py --audit
# same plus pip-audit in the Poetry env; non-zero exit if known CVEs (same as CI)
```

CI refreshes `pip`, `setuptools`, and `msgpack` in the venv before audit (`pip-audit` reports those packages even though they are not in `pyproject.toml`; `msgpack` is pulled in by `pip-audit` itself).

On Windows, if `npm` is missing or the shim does not start from `subprocess`, the frontend block is marked skipped. For a full frontend picture, run the script where `npm` is on PATH, or run `npm outdated` in `frontend/` yourself.

A full `poetry run pytest tests/` matching CI (Postgres + Redis, `DATABASE_URL_TEST`, optionally `RUN_REDIS_INTEGRATION_TESTS=1`, for e2e `FRONTEND_E2E_URL` / preview autostart) is documented in [`documentation/DEVELOPMENT.md`](./documentation/DEVELOPMENT.md). A dedicated test database with `alembic upgrade head` is closer to CI than a live dev DB with stale or partial data — otherwise service tests can fail on business invariants (for example no default cash register on the clinic).

**`DATABASE_URL` / `DATABASE_URL_TEST`:** CI sets both, or only `DATABASE_URL` — then pytest substitutes the database name `dental_booking_test` (same host and password). Preferred name: `dental_booking_test`. Table cleanup (`TRUNCATE` in `tests/conftest.py`) requires the URL database name to **contain the substring `test`**, so a mistaken run against a non-test database is less likely.

Also see [`README.md`](./README.md) (CI section), [`CONTRIBUTING.md`](./CONTRIBUTING.md), and [`documentation/VPS_IMAGE_AND_DATA.md`](./documentation/VPS_IMAGE_AND_DATA.md).
