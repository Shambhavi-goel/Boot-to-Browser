$ErrorActionPreference = "Stop"

$taskName = "BootToBrowserCopilot"
$projectFolder = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectFolder "venv\Scripts\python.exe"
$mainScript = Join-Path $projectFolder "main.py"

if (-not (Test-Path $pythonExe)) {
    throw "Virtual environment Python not found: $pythonExe"
}

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

schtasks.exe /Create /TN $taskName /SC ONLOGON /RU $currentUser /TR ('"' + $pythonExe + '" "' + $mainScript + '"') /DELAY 0000:10 /F

$task = Get-ScheduledTask -TaskName $taskName
$task.Settings.RestartCount = 3
$task.Settings.RestartInterval = "PT1M"
Set-ScheduledTask -TaskName $taskName -Settings $task.Settings

Write-Host "Registered Task Scheduler task $taskName for $currentUser"
