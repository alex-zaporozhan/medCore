# Full backend pytest + browser E2E (Playwright), parity with .github/workflows/backend-ci.yml / Jenkinsfile.
# Prerequisites: Node 20+, Poetry, Postgres + Redis (see documentation/DEVELOPMENT.md).
#
# From repo root:
#   pwsh -File scripts/dev/full_pytest_with_frontend_e2e.ps1
#   pwsh -File scripts/dev/full_pytest_with_frontend_e2e.ps1 --maxfail=1
# Extra pytest flags: append after script name (they land in $args).

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

function Import-RepoDotEnv {
    $envFile = Join-Path $Root ".env"
    if (-not (Test-Path $envFile)) { return }
    foreach ($line in Get-Content $envFile) {
        $t = $line.Trim()
        if ($t -eq "" -or $t.StartsWith("#")) { continue }
        $i = $t.IndexOf("=")
        if ($i -lt 1) { continue }
        $k = $t.Substring(0, $i).Trim()
        $v = $t.Substring($i + 1).Trim()
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        if ([string]::IsNullOrWhiteSpace($k)) { continue }
        if ($null -ne [Environment]::GetEnvironmentVariable($k, "Process")) { continue }
        [Environment]::SetEnvironmentVariable($k, $v, "Process")
    }
}

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL_TEST)) {
    Import-RepoDotEnv
}

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL_TEST)) {
    Write-Error "DATABASE_URL_TEST is required (set in .env or export). Example: postgresql+asyncpg://postgres:postgres@127.0.0.1:5442/dental_booking_test"
}

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    [Environment]::SetEnvironmentVariable("DATABASE_URL", $env:DATABASE_URL_TEST, "Process")
}

if ([string]::IsNullOrWhiteSpace($env:TESTING)) { [Environment]::SetEnvironmentVariable("TESTING", "1", "Process") }
if ([string]::IsNullOrWhiteSpace($env:RUN_REDIS_INTEGRATION_TESTS)) {
    [Environment]::SetEnvironmentVariable("RUN_REDIS_INTEGRATION_TESTS", "1", "Process")
}
if ([string]::IsNullOrWhiteSpace($env:SECRET_KEY)) {
    [Environment]::SetEnvironmentVariable("SECRET_KEY", "ci-secret-key-32-chars-minimum-xx", "Process")
}
if ([string]::IsNullOrWhiteSpace($env:JWT_SECRET_KEY)) {
    [Environment]::SetEnvironmentVariable("JWT_SECRET_KEY", "ci-jwt-secret-key-32-chars-minimum", "Process")
}
if ([string]::IsNullOrWhiteSpace($env:PLATFORM_BILLING_WEBHOOK_SECRET)) {
    [Environment]::SetEnvironmentVariable("PLATFORM_BILLING_WEBHOOK_SECRET", "test-platform-billing-webhook-secret", "Process")
}

$PreviewHost = if ($env:PREVIEW_HOST) { $env:PREVIEW_HOST } else { "127.0.0.1" }
$PreviewPort = if ($env:PREVIEW_PORT) { $env:PREVIEW_PORT } else { "4173" }
if ([string]::IsNullOrWhiteSpace($env:FRONTEND_E2E_URL)) {
    [Environment]::SetEnvironmentVariable("FRONTEND_E2E_URL", "http://${PreviewHost}:${PreviewPort}", "Process")
}

$frontend = Join-Path $Root "frontend"
Set-Location $frontend
npm ci
npm run build
Set-Location $Root

poetry run playwright install chromium

$previewLog = Join-Path ([System.IO.Path]::GetTempPath()) "vite-preview-dental-booking.log"
$cmdLine = "cd /d `"$frontend`" && npm run preview -- --host $PreviewHost --port $PreviewPort > `"$previewLog`" 2>&1"
$previewProc = Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmdLine) -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 6

try {
    if ($args.Count -gt 0) {
        poetry run pytest tests/ -q --tb=short @args
    } else {
        poetry run pytest tests/ -q --tb=short
    }
} finally {
    if ($null -ne $previewProc -and -not $previewProc.HasExited) {
        Stop-Process -Id $previewProc.Id -Force -ErrorAction SilentlyContinue
    }
}
