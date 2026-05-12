# 设置每日工作记忆同步计划任务

$TaskName = "WorkBuddy-IMA-Sync"
$PythonScriptPath = "C:\Users\green\WorkBuddy\Claw\sync_daily_memory.py"
$WorkingDirectory = "C:\Users\green\WorkBuddy\Claw"
$TriggerTime = "18:00"  # 每天下午6点

# 检查任务是否已存在
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "[警告] 计划任务 '$TaskName' 已存在，将重新创建..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建触发器（每天指定时间）
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime

# 创建操作（运行Python脚本）
$Action = New-ScheduledTaskAction -Execute "python" -Argument "`"$PythonScriptPath`"" -WorkingDirectory $WorkingDirectory

# 设置任务设置
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 注册任务
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

try {
    Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force
    Write-Host "[OK] 计划任务创建成功！"
    Write-Host "   任务名称: $TaskName"
    Write-Host "   执行时间: 每天 $TriggerTime"
    Write-Host "   脚本路径: $PythonScriptPath"
    Write-Host ""
    Write-Host "您可以通过以下命令管理任务:"
    Write-Host "   - 查看任务: Get-ScheduledTask -TaskName '$TaskName'"
    Write-Host "   - 运行任务: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "   - 删除任务: Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
} catch {
    Write-Host "[错误] 创建计划任务失败: $_"
    exit 1
}