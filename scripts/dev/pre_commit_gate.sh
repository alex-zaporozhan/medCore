#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/.tmp_ci_logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/local-pre-commit-gate.log"

echo "Local pre-commit gate started at $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${LOG_FILE}"

cd "${ROOT_DIR}"
echo "==> Ruff check (changed files in src/tests)" | tee -a "${LOG_FILE}"
if git diff --cached --name-only | grep -E '^(src|tests)/.*\.py$' >/dev/null 2>&1; then
  PY_CHANGED="$(git diff --cached --name-only | grep -E '^(src|tests)/.*\.py$' | tr '\n' ' ')"
  poetry run ruff check ${PY_CHANGED} 2>&1 | tee -a "${LOG_FILE}"
else
  echo "No staged Python files in src/tests. Skipping ruff." | tee -a "${LOG_FILE}"
fi

echo "==> Frontend ESLint (changed files in frontend)" | tee -a "${LOG_FILE}"
if git diff --cached --name-only | grep -E '^frontend/.*\.(ts|tsx|js|jsx)$' >/dev/null 2>&1; then
  (
    cd frontend
    npm run lint
  ) 2>&1 | tee -a "${LOG_FILE}"
else
  echo "No staged frontend code files. Skipping frontend lint." | tee -a "${LOG_FILE}"
fi

echo "Local pre-commit gate passed." | tee -a "${LOG_FILE}"
