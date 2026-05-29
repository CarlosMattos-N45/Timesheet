$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

dotnet publish "$root/src/Timesheet.Agent.Service" -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o "$root/dist/service"
dotnet publish "$root/src/Timesheet.Agent.Ui" -c Release -r win-x64 --self-contained -p:PublishSingleFile=true -o "$root/dist/ui"

if (-not (Test-Path "$root/dist/service/TimesheetAgent.exe")) {
    Write-Error "TimesheetAgent.exe nao gerado"
    exit 1
}
if (-not (Test-Path "$root/dist/ui/TimesheetAgentUi.exe")) {
    Write-Error "TimesheetAgentUi.exe nao gerado"
    exit 1
}

Write-Host "[publish-agent] OK: service + ui"
