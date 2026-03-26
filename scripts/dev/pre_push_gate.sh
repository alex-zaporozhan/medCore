#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/.tmp_ci_logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/local-pre-push-gate.log"

run_step() {
  local title="$1"
  shift
  echo "==> ${title}" | tee -a "${LOG_FILE}"
  "$@" 2>&1 | tee -a "${LOG_FILE}"
}

echo "Local pre-push gate started at $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${LOG_FILE}"

cd "${ROOT_DIR}"
run_step "Backend lint (ruff)" poetry run ruff check src tests
run_step "Backend tenant audit" poetry run python scripts/audit_tenant_columns.py
run_step "Backend type-check (mypy JWT module)" poetry run mypy src/core/security.py --ignore-missing-imports --follow-imports=skip
run_step "Backend tests (pytest, no e2e)" poetry run pytest tests/ -q --tb=short --ignore=tests/e2e --maxfail=1

cd "${ROOT_DIR}/frontend"
run_step "Frontend lint" npm run lint
run_step "Frontend tests (vitest once)" npm run test -- --run
run_step "Frontend build" npm run build

echo "Local pre-push gate passed." | tee -a "${LOG_FILE}"
