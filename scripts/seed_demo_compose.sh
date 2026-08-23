# Seed demo users into the Compose Postgres (no host Poetry required).
# Prerequisites: `docker compose up -d --build --wait` from the repo root.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
docker compose exec -T backend python -m src.scripts.seed_rbac_baseline
docker compose exec -T backend python -m src.scripts.seed_multi_tenant_showcase
echo "Demo staff: owner.kazan@showcase-mt.demo / ShowcaseMT2026!  ->  /admin/login"
