#!/usr/bin/env bash
# Start FastAPI on :8000 (vite preview proxies /api and /health there) then vite preview on :4173, then exec pytest.
# Used by GitHub Actions when FRONTEND_E2E_URL points at preview (Playwright browser E2E).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

poetry run alembic upgrade head

# Uvicorn runs in a separate process from pytest. With TESTING=1 the async engine is
# deferred to init_engine_for_testing() (pytest ASGI harness only), so AsyncSessionLocal
# stays None here and any DB route (e.g. GET /api/v1/clinics) becomes 500. Use a non-test
# flag for this long-lived API only; pytest still runs with TESTING=1 from the job env.
TESTING=0 poetry run uvicorn src.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn-e2e.log 2>&1 &
echo $! > /tmp/uvicorn-e2e.pid
# Wait until API accepts connections (preview proxy targets this).
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    break
  fi
  sleep 0.3
done

cd frontend
npm run preview -- --host 127.0.0.1 --port 4173 > /tmp/vite-preview.log 2>&1 &
echo $! > /tmp/vite-preview.pid
cd ..
sleep 6

"$@"
exit $?
