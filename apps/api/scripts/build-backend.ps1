#Requires -Version 5.1
<#
.SYNOPSIS
    Build script: bundles the React SPA + FastAPI backend into a single
    Windows executable (apps/api/dist/timesheet-backend.exe).

.DESCRIPTION
    Steps:
    1. Build the React SPA (npm run build inside apps/web).
    2. Copy apps/web/dist/** → apps/api/app/static/ (wipes previous build).
    3. Run PyInstaller with timesheet-backend.spec → dist/timesheet-backend.exe.

    Prerequisites:
    - Node.js and npm available in PATH.
    - Python + pyinstaller installed (pip install pyinstaller, or via the
      [build] optional-dependencies group in pyproject.toml).
    - Run from the repository root or from apps/api/.

.EXAMPLE
    # From the repository root:
    powershell -ExecutionPolicy Bypass -File apps/api/scripts/build-backend.ps1

    # From apps/api/:
    powershell -ExecutionPolicy Bypass -File scripts/build-backend.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Resolve paths ────────────────────────────────────────────────────────────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path   # apps/api/scripts/
$apiDir    = Split-Path -Parent $scriptDir                      # apps/api/
$repoRoot  = Split-Path -Parent (Split-Path -Parent $apiDir)   # repo root

$webDir     = Join-Path $repoRoot 'apps\web'
$webDist    = Join-Path $webDir   'dist'
$staticDir  = Join-Path $apiDir   'app\static'
$specFile   = Join-Path $apiDir   'timesheet-backend.spec'
$distDir    = Join-Path $apiDir   'dist'

Write-Host "[build] Repo root : $repoRoot"
Write-Host "[build] Web dir   : $webDir"
Write-Host "[build] API dir   : $apiDir"

# ── Step 1 — build React SPA ────────────────────────────────────────────────────
Write-Host ""
Write-Host "[build] Step 1/3 — npm run build (apps/web)"
Push-Location $webDir
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

# ── Step 2 — copy dist → app/static ─────────────────────────────────────────────
Write-Host ""
Write-Host "[build] Step 2/3 — copy apps/web/dist → apps/api/app/static"

if (-not (Test-Path $webDist)) {
    throw "apps/web/dist not found after npm build. Check vite output."
}

# Wipe old static content to avoid stale assets.
if (Test-Path $staticDir) {
    Remove-Item -Recurse -Force $staticDir
}
New-Item -ItemType Directory -Force $staticDir | Out-Null

Copy-Item -Recurse -Force (Join-Path $webDist '*') $staticDir
Write-Host "[build] Copied web assets to $staticDir"

# ── Step 3 — PyInstaller ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "[build] Step 3/3 — pyinstaller timesheet-backend.spec"
Push-Location $apiDir
try {
    python -m PyInstaller $specFile --distpath dist --workpath build\pyinstaller --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }
} finally {
    Pop-Location
}

$exePath = Join-Path $distDir 'timesheet-backend.exe'
if (-not (Test-Path $exePath)) {
    throw "Expected output not found: $exePath"
}

Write-Host ""
Write-Host "[build] Done. Executable: $exePath"
