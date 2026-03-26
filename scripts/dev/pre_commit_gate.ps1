$ErrorActionPreference = "Stop"

$root = (Resolve-Path "$PSScriptRoot\..\..").Path
$logDir = Join-Path $root ".tmp_ci_logs"
$logFile = Join-Path $logDir "local-pre-commit-gate.log"

if (!(Test-Path $logDir)) {
  New-Item -Path $logDir -ItemType Directory | Out-Null
}

"Local pre-commit gate started at $(Get-Date -AsUTC -Format o)" | Out-File -FilePath $logFile -Encoding utf8

$staged = git diff --cached --name-only

$pyChanged = $staged | Where-Object { $_ -match '^(src|tests)/.*\.py$' }
if ($pyChanged.Count -gt 0) {
  "==> Ruff check (changed files in src/tests)" | Tee-Object -FilePath $logFile -Append
  $pyArgs = ($pyChanged -join " ")
  Invoke-Expression "poetry run ruff check $pyArgs *>&1 | Tee-Object -FilePath '$logFile' -Append"
  if ($LASTEXITCODE -ne 0) { throw "Ruff failed" }
} else {
  "No staged Python files in src/tests. Skipping ruff." | Tee-Object -FilePath $logFile -Append
}

$feChanged = $staged | Where-Object { $_ -match '^frontend/.*\.(ts|tsx|js|jsx)$' }
if ($feChanged.Count -gt 0) {
  "==> Frontend ESLint (changed files in frontend)" | Tee-Object -FilePath $logFile -Append
  Push-Location (Join-Path $root "frontend")
  try {
    Invoke-Expression "npm run lint *>&1 | Tee-Object -FilePath '$logFile' -Append"
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed" }
  } finally {
    Pop-Location
  }
} else {
  "No staged frontend code files. Skipping frontend lint." | Tee-Object -FilePath $logFile -Append
}

"Local pre-commit gate passed." | Tee-Object -FilePath $logFile -Append
