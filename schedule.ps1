param([string]$Time='09:00')
$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run start.cmd first.' }
$script=Join-Path $PSScriptRoot 'app.py'
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$script+'" run --mode live') -WorkingDirectory $PSScriptRoot
$trigger=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $Time
$principal=New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName 'WeeklyDeliverySimulation' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'LOCAL SIMULATION ONLY: real Excel + Jev, test mailbox' -ErrorAction Stop
