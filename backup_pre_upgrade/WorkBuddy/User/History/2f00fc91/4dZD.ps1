# Setup daily work memory sync scheduled task

$TaskName = "WorkBuddy-IMA-Sync"
$PythonScriptPath = "C:\Users\green\WorkBuddy\Claw\sync_daily_memory.py"
$WorkingDirectory = "C:\Users\green\WorkBuddy\Claw"
$TriggerTime = "18:00"  # Daily at 6 PM

# Check if task already exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "[WARN] Scheduled task '$TaskName' already exists, recreating..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create trigger (daily at specified time)
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# Create action (run Python script)
$Action = New-ScheduledTaskAction -Execute "python" -Argument "`"$PythonScriptPath`"" -WorkingDirectory $WorkingDirectory

# Create task settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register task
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

try {
    Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force
    Write-Host "[OK] Scheduled task created successfully!"
    Write-Host "   Task name: $TaskName"
    Write-Host "   Run time: Daily at $TriggerTime"
    Write-Host "   Script: $PythonScriptPath"
    Write-Host ""
    Write-Host "Management commands:"
    Write-Host "   - View task: Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "   - Run task: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "   - Delete task: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
} catch {
    Write-Host "[ERROR] Failed to create scheduled task: $_"
    exit 1
}