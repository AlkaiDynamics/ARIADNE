# Run on your Windows machine only when you want ARIADNE to start at sign-in.
$ariRoot = Split-Path -Parent $PSScriptRoot
$ariPython = (Get-Command python -ErrorAction Stop).Source
$ariAction = New-ScheduledTaskAction -Execute $ariPython -Argument ('"' + (Join-Path $ariRoot 'warden.py') + '" serve') -WorkingDirectory $ariRoot
$ariTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$ariSettings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'ARIADNE Local Research' -Action $ariAction -Trigger $ariTrigger -Settings $ariSettings -Description 'Local algorithm-only acquisition and evidence research' -Force
