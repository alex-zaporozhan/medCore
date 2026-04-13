#Requires -Version 5.1
<#
.SYNOPSIS
  Build backend + frontend images locally, then push to Docker Hub (password at prompt).

.DESCRIPTION
  Safer default for VPS: no Hub token in GitHub unless you choose GHA. Order is always:
  1) docker build (both images) — fails fast;
  2) docker login (interactive password);
  3) docker push (both tags).

.PARAMETER Tag
  Image tag for both images (default: latest).

.PARAMETER DockerHubUser
  Docker Hub namespace (username or org). If empty, uses env DOCKERHUB_USERNAME or prompts.

.EXAMPLE
  .\scripts\docker_hub_release.ps1 -Tag v1.0.0
  $env:DOCKERHUB_USERNAME = 'myuser'; .\scripts\docker_hub_release.ps1 -Tag demo
#>
param(
    [string]$Tag = "latest",
    [string]$DockerHubUser = $env:DOCKERHUB_USERNAME
)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))

if (-not $DockerHubUser -or $DockerHubUser.Trim() -eq "") {
    $DockerHubUser = Read-Host "Docker Hub username (namespace)"
}
$DockerHubUser = $DockerHubUser.Trim()
if ($DockerHubUser -eq "") {
    Write-Error "Docker Hub username is required."
}

$backend = "${DockerHubUser}/dental-booking-backend:${Tag}"
$frontend = "${DockerHubUser}/dental-booking-frontend:${Tag}"

Write-Host "Building backend -> $backend"
docker build -t $backend -f Dockerfile .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building frontend -> $frontend"
docker build -t $frontend -f Dockerfile ./frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Build OK. Docker Hub login (password/token at prompt; input is hidden)..."
docker login docker.io -u $DockerHubUser
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Pushing $backend"
docker push $backend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Pushing $frontend"
docker push $frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. On the VPS set in .env, for example:"
Write-Host "  BACKEND_IMAGE=docker.io/${backend}"
Write-Host "  FRONTEND_IMAGE=docker.io/${frontend}"
