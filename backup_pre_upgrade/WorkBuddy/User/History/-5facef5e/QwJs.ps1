$allWB = Get-CimInstance Win32_Process -Filter "Name='WorkBuddy.exe'"

Write-Output "=== 1. Process Parent-Child ==="
foreach ($p in $allWB) {
    $parentName = ""
    try {
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
        if ($parent) { $parentName = $parent.Name }
    } catch {}
    $mem = 0
    try { $mem = [math]::Round((Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue).WorkingSet64/1MB,1) } catch {}
    $type = "main"
    if ($p.CommandLine -match "--type=([^ ]+)") { $type = $Matches[1] }
    Write-Output "PID=$($p.ProcessId) ParentPID=$($p.ParentProcessId) Parent=$parentName Mem=${mem}MB Type=$type"
}

Write-Output ""
Write-Output "=== 2. Type Distribution ==="
$types = @{}
foreach ($p in $allWB) {
    $type = "main"
    if ($p.CommandLine -match "--type=([^ ]+)") { $type = $Matches[1] }
    if (-not $types.ContainsKey($type)) { $types[$type] = [PSCustomObject]@{Count=0;TotalMem=0} }
    $types[$type].Count++
    $mem = 0
    try { $mem = [math]::Round((Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue).WorkingSet64/1MB,1) } catch {}
    $types[$type].TotalMem += $mem
}
foreach ($kv in $types.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value.Count) procs, $($kv.Value.TotalMem)MB total"
}

Write-Output ""
Write-Output "=== 3. Main Processes (no --type) ==="
$mainProcs = $allWB | Where-Object { $_.CommandLine -notmatch "--type=" }
Write-Output "Count: $($mainProcs.Count)"
foreach ($p in $mainProcs) {
    Write-Output "  PID=$($p.ProcessId) ParentPID=$($p.ParentProcessId)"
}

Write-Output ""
Write-Output "=== 4. Unique Window Configs ==="
$windows = @{}
foreach ($p in $allWB) {
    if ($p.CommandLine -match "vscode-window-config=([^ ]+)") {
        $wid = $Matches[1]
        if (-not $windows.ContainsKey($wid)) { $windows[$wid] = 0 }
        $windows[$wid]++
    }
}
Write-Output "Unique windows: $($windows.Count)"
foreach ($kv in $windows.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value) processes"
}

Write-Output ""
Write-Output "=== 5. User Data Dirs ==="
$dirs = @{}
foreach ($p in $allWB) {
    $pattern = 'user-data-dir="([^"]+)"'
    if ($p.CommandLine -match $pattern) {
        $d = $Matches[1]
        if (-not $dirs.ContainsKey($d)) { $dirs[$d] = 0 }
        $dirs[$d]++
    }
}
foreach ($kv in $dirs.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value) processes"
}

Write-Output ""
Write-Output "=== 6. Executable Paths ==="
$paths = @{}
foreach ($p in $allWB) {
    $exePath = $p.ExecutablePath
    if (-not $paths.ContainsKey($exePath)) { $paths[$exePath] = 0 }
    $paths[$exePath]++
}
foreach ($kv in $paths.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value) processes"
}
