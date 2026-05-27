#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$apiDir = Join-Path (Join-Path $PSScriptRoot "..") "apps\api"
$process = $null

try {
    # Start uvicorn em background
    Push-Location $apiDir
    $process = Start-Process -FilePath "uvicorn" `
        -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8765" `
        -PassThru -WindowStyle Hidden
    Pop-Location

    # Poll /health ate 10s (contador limitado, evitar loop infinito)
    $maxAttempts = 20  # 20 * 500ms = 10s
    $attempt = 0
    $ready = $false
    while ($attempt -lt $maxAttempts -and -not $ready) {
        Start-Sleep -Milliseconds 500
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/v1/health" -TimeoutSec 2
            if ($response.status -eq "ok" -and $response.version -eq "0.1.0") {
                $ready = $true
            }
        } catch {
            # ignora — backend ainda subindo
        }
        $attempt++
    }

    if (-not $ready) {
        Write-Error "[API SMOKE FAIL] /health nao respondeu 200 em 10s ou body invalido"
        exit 1
    }

    Write-Host "[API SMOKE OK] /health respondeu 200 com status=ok version=0.1.0"
    exit 0
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}
