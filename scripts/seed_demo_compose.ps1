# Seed demo users into the Compose Postgres (no host Poetry required).
# Prerequisites: docker compose up -d --build --wait  (from repo root)
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
if (-not (Test-Path ".\docker-compose.yml")) {
    throw "docker-compose.yml not found at $repoRoot"
}
docker compose exec -T backend python -m src.scripts.seed_rbac_baseline
if ($LASTEXITCODE -ne 0) { throw "seed_rbac_baseline failed" }
docker compose exec -T backend python -m src.scripts.seed_multi_tenant_showcase
if ($LASTEXITCODE -ne 0) { throw "seed_multi_tenant_showcase failed" }
Write-Host "Demo staff: owner.kazan@showcase-mt.demo / ShowcaseMT2026!  ->  /admin/login"
