#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$agentDir = Join-Path (Join-Path $PSScriptRoot "..") "apps\agent"
$dotnet = "C:\Program Files\dotnet\dotnet.exe"

if (-not (Test-Path $dotnet)) {
    $dotnetCmd = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($dotnetCmd) {
        $dotnet = $dotnetCmd.Source
    } else {
        Write-Error "[AGENT SMOKE FAIL] dotnet nao encontrado no PATH nem em C:\Program Files\dotnet\"
        exit 1
    }
}

Push-Location $agentDir
try {
    Write-Host "[AGENT SMOKE] dotnet build..."
    & $dotnet build Timesheet.Agent.sln -c Debug
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[AGENT SMOKE FAIL] dotnet build falhou"
        exit 1
    }

    Write-Host "[AGENT SMOKE] dotnet test..."
    & $dotnet test Timesheet.Agent.sln -c Debug --no-restore
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[AGENT SMOKE FAIL] dotnet test falhou"
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "[AGENT SMOKE OK] build e testes passaram"
exit 0
