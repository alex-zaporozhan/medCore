$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$logDir = Join-Path $root ".tmp_ci_logs"
$logFile = Join-Path $logDir "local-pre-push-gate.log"

if (!(Test-Path $logDir)) {
  New-Item -Path $logDir -ItemType Directory | Out-Null
}

function Run-Step {
  param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][string]$Command
  )

  Write-Host "==> $Title"
  "==> $Title" | Out-File -FilePath $logFile -Append -Encoding utf8
  Invoke-Expression "$Command *>&1 | Tee-Object -FilePath '$logFile' -Append"
  if ($LASTEXITCODE -ne 0) {
    throw "Step failed: $Title"
  }
}

"Local pre-push gate started at $(Get-Date -AsUTC -Format o)" | Out-File -FilePath $logFile -Encoding utf8

Set-Location $root
Run-Step -Title "Backend lint (ruff)" -Command "poetry run ruff check src tests"
Run-Step -Title "Backend tenant audit" -Command "poetry run python scripts/audit_tenant_columns.py"
Run-Step -Title "Backend type-check (mypy JWT module)" -Command "poetry run mypy src/core/security.py --ignore-missing-imports --follow-imports=skip"
Run-Step -Title "Backend tests (pytest, no e2e)" -Command "poetry run pytest tests/ -q --tb=short --ignore=tests/e2e --maxfail=1"

Set-Location (Join-Path $root "frontend")
Run-Step -Title "Frontend lint" -Command "npm run lint"
Run-Step -Title "Frontend tests (vitest once)" -Command "npm run test -- --run"
Run-Step -Title "Frontend build" -Command "npm run build"

Set-Location $root
"Local pre-push gate passed." | Tee-Object -FilePath $logFile -Append
