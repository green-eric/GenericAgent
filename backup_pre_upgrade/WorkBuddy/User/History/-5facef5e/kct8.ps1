Write-Output "=== 1. WorkBuddy 进程完整命令行 ==="
Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)"
    Write-Output "--- PID=$($_.Id) Mem=${mem}MB ---"
    Write-Output "Path: $($wmi.ExecutablePath)"
    Write-Output "Cmd:  $($wmi.CommandLine)"
    Write-Output ""
}

Write-Output "=== 2. 检查是否有多个 WorkBuddy 实例（不同路径）==="
Get-CimInstance Win32_Process -Filter "Name='WorkBuddy.exe'" | Select-Object ProcessId, ExecutablePath | Format-Table -AutoSize

Write-Output "=== 3. 检查 WorkBuddy 安装目录 ==="
$wbPaths = @(
    "C:\Users\green\AppData\Local\Programs\WorkBuddy",
    "C:\Program Files\WorkBuddy"
)
foreach ($p in $wbPaths) {
    if (Test-Path $p) {
        Write-Output "Found: $p"
        Get-ChildItem $p -Filter "WorkBuddy.exe" | ForEach-Object {
            Write-Output "  Version: $($_.VersionInfo.FileVersion)  Size: $([math]::Round($_.Length/1MB,1))MB"
        }
    }
}

Write-Output ""
Write-Output "=== 4. 检查开机自启中的 WorkBuddy ==="
$runKeys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
)
foreach ($key in $runKeys) {
    Get-ItemProperty $key -ErrorAction SilentlyContinue | Get-Member -MemberType NoteProperty | Where-Object { $_.Name -match "WorkBuddy" } | ForEach-Object {
        $val = (Get-ItemProperty $key).$($_.Name)
        Write-Output "$key\$($_.Name) = $val"
    }
}

Write-Output ""
Write-Output "=== 5. 检查计划任务中的 WorkBuddy ==="
Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match "WorkBuddy" } | ForEach-Object {
    Write-Output "Task: $($_.TaskName) State: $($_.State)"
}

Write-Output ""
Write-Output "=== 6. 检查 WorkBuddy 数据目录大小 ==="
$dataDir = "C:\Users\green\AppData\Roaming\WorkBuddy"
if (Test-Path $dataDir) {
    $size = (Get-ChildItem $dataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Output "Data dir size: $([math]::Round($size/1MB,1))MB"
    Get-ChildItem $dataDir -Directory | ForEach-Object {
        $dsize = (Get-ChildItem $_.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        Write-Output "  $($_.Name): $([math]::Round($dsize/1MB,1))MB"
    }
}
