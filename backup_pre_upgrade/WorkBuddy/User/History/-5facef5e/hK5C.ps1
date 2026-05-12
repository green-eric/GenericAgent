Write-Output "=== 1. WorkBuddy 进程父子关系 ==="
$allWB = Get-CimInstance Win32_Process -Filter "Name='WorkBuddy.exe'"
foreach ($p in $allWB) {
    $parentName = ""
    $parentCmd = ""
    try {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent) {
            $parentName = $parent.Name
            $parentCmd = $parent.CommandLine
        }
    } catch {}
    $mem = 0
    try { $mem = [math]::Round((Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue).WorkingSet64/1MB,1) } catch {}
    Write-Output "PID=$($p.ProcessId)  ParentPID=$($p.ParentProcessId)  Parent=$parentName  Mem=${mem}MB"
    # 只显示命令行中的关键部分
    $cmd = $p.CommandLine
    if ($cmd -match "--type=([^ ]+)") { Write-Output "  type=$($Matches[1])" }
    if ($cmd -match "vscode-window-config=([^ ]+)") { Write-Output "  window=$($Matches[1])" }
    if ($cmd -match "renderer-client-id=(\d+)") { Write-Output "  client-id=$($Matches[1])" }
}

Write-Output ""
Write-Output "=== 2. 统计 type 分布 ==="
$types = @{}
foreach ($p in $allWB) {
    $cmd = $p.CommandLine
    $type = "unknown"
    if ($cmd -match "--type=([^ ]+)") { $type = $Matches[1] }
    if (-not $types.ContainsKey($type)) { $types[$type] = 0 }
    $types[$type]++
}
foreach ($kv in $types.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value)"
}

Write-Output ""
Write-Output "=== 3. 检查是否有多个主进程（无 --type 参数）==="
$mainProcs = $allWB | Where-Object { $_.CommandLine -notmatch "--type=" }
Write-Output "Main processes (no --type): $($mainProcs.Count)"
foreach ($p in $mainProcs) {
    Write-Output "  PID=$($p.ProcessId)  ParentPID=$($p.ParentProcessId)"
    Write-Output "  CMD: $($p.CommandLine)"
}

Write-Output ""
Write-Output "=== 4. 检查 vscode-window-config（窗口ID）==="
$windows = @{}
foreach ($p in $allWB) {
    if ($p.CommandLine -match "vscode-window-config=([^ ]+)") {
        $wid = $Matches[1]
        if (-not $windows.ContainsKey($wid)) { $windows[$wid] = @() }
        $windows[$wid] += $p.ProcessId
    }
}
Write-Output "Unique window configs: $($windows.Count)"
foreach ($kv in $windows.GetEnumerator()) {
    Write-Output "  Window $($kv.Key): $($kv.Value.Count) processes"
}

Write-Output ""
Write-Output "=== 5. 检查 user-data-dir ==="
$dirs = @{}
foreach ($p in $allWB) {
    if ($p.CommandLine -match "user-data-dir=\"([^\"]+)\"") {
        $d = $Matches[1]
        if (-not $dirs.ContainsKey($d)) { $dirs[$d] = 0 }
        $dirs[$d]++
    }
}
foreach ($kv in $dirs.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value) processes"
}
