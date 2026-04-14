#!/usr/bin/env bash
# Full backend pytest + browser E2E (Playwright), same shape as .github/workflows/backend-ci.yml and Jenkinsfile.
# Prerequisites: Node 20+, Poetry, Postgres+Redis reachable (see documentation/DEVELOPMENT.md).
# Usage (from repo root):
#   bash scripts/dev/full_pytest_with_frontend_e2e.sh
#   bash scripts/dev/full_pytest_with_frontend_e2e.sh --maxfail=1 -q
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ -z "${DATABASE_URL_TEST:-}" ]] && [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "${ROOT_DIR}/.env"
  set +a
fi

if [[ -z "${DATABASE_URL_TEST:-}" ]]; then
  echo "DATABASE_URL_TEST is required (set in .env or export before running)."
  echo "Example: postgresql+asyncpg://postgres:postgres@localhost:5442/dental_booking_test"
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  export DATABASE_URL="${DATABASE_URL_TEST}"
fi

export TESTING="${TESTING:-1}"
export RUN_REDIS_INTEGRATION_TESTS="${RUN_REDIS_INTEGRATION_TESTS:-1}"
export SECRET_KEY="${SECRET_KEY:-ci-secret-key-32-chars-minimum-xx}"
export JWT_SECRET_KEY="${JWT_SECRET_KEY:-ci-jwt-secret-key-32-chars-minimum}"
export PLATFORM_BILLING_WEBHOOK_SECRET="${PLATFORM_BILLING_WEBHOOK_SECRET:-test-platform-billing-webhook-secret}"

PREVIEW_HOST="${PREVIEW_HOST:-127.0.0.1}"
PREVIEW_PORT="${PREVIEW_PORT:-4173}"
export FRONTEND_E2E_URL="${FRONTEND_E2E_URL:-http://${PREVIEW_HOST}:${PREVIEW_PORT}}"

cd "${ROOT_DIR}/frontend"
npm ci
npm run build
cd "${ROOT_DIR}"

poetry run playwright install chromium

PREVIEW_LOG="${TMPDIR:-/tmp}/vite-preview-dental-booking.log"
cd "${ROOT_DIR}/frontend"
npm run preview -- --host "${PREVIEW_HOST}" --port "${PREVIEW_PORT}" >"${PREVIEW_LOG}" 2>&1 &
PREVIEW_PID=$!
echo "${PREVIEW_PID}" >"${TMPDIR:-/tmp}/vite-preview-dental-booking.pid"
cd "${ROOT_DIR}"

cleanup() {
  if [[ -n "${PREVIEW_PID:-}" ]] && kill -0 "${PREVIEW_PID}" 2>/dev/null; then
    kill "${PREVIEW_PID}" 2>/dev/null || true
    wait "${PREVIEW_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

sleep 6

poetry run pytest tests/ -q --tb=short "$@"
