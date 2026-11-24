$ErrorActionPreference = "Stop"

$taskName = "BootToBrowserCopilot"
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($null -ne $task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed Task Scheduler task $taskName"
} else {
    Write-Host "Task Scheduler task $taskName is not registered"
}
