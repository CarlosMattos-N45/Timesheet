#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$webDir = Join-Path (Join-Path $PSScriptRoot "..") "apps\web"

Push-Location $webDir
try {
    Write-Host "[WEB SMOKE] tsc --noEmit..."
    node "node_modules\typescript\bin\tsc" --noEmit
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[WEB SMOKE FAIL] tsc --noEmit falhou"
        exit 1
    }

    Write-Host "[WEB SMOKE] vite build..."
    node "node_modules\vite\bin\vite.js" build
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[WEB SMOKE FAIL] vite build falhou"
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "[WEB SMOKE OK] build de producao passou"
exit 0
