Write-Output "=== WorkBuddy 进程详情 ==="
$wbProcs = Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending

foreach ($p in $wbProcs) {
    $wmi = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)"
    $parentName = ""
    try { $parentName = (Get-Process -Id $wmi.ParentProcessId -ErrorAction SilentlyContinue).ProcessName } catch {}
    $mem = [math]::Round($p.WorkingSet64/1MB,1)
    $startTime = $p.StartTime
    Write-Output "---"
    Write-Output "PID=$($p.Id)  Mem=${mem}MB  StartTime=$startTime"
    Write-Output "ParentPID=$($wmi.ParentProcessId)  ParentName=$parentName"
    Write-Output "CMD: $($wmi.CommandLine)"
}

Write-Output ""
Write-Output "=== 进程树（父子关系） ==="
$all = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "WorkBuddy.exe" }
foreach ($proc in $all) {
    $indent = ""
    $cur = $proc
    $depth = 0
    while ($cur.ParentProcessId -ne 0 -and $depth -lt 5) {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($cur.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($null -eq $parent -or $parent.Name -ne "WorkBuddy.exe") { break }
        $indent += "  "
        $cur = $parent
        $depth++
    }
    $mem = [math]::Round((Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue).WorkingSet64/1MB,1)
    Write-Output "${indent}PID=$($proc.ProcessId) ParentPID=$($proc.ParentProcessId) Mem=${mem}MB"
    Write-Output "${indent}  CMD: $($proc.CommandLine)"
}
